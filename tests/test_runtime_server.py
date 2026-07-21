from __future__ import annotations

import importlib.util
import inspect
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

from acheon.compiler import ContextCompiler
from acheon.demo import seed_demo
from acheon.runtime import (
    DEVELOPER_INSTRUCTIONS,
    OpenAIResponsesAdapter,
    RuntimeCallError,
)
from acheon.server import make_server
from acheon.store import MemoryStore


class FakeResponses:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def sample_packet():
    with MemoryStore() as store:
        seed_demo(store)
        return ContextCompiler(store).compile(
            query="What release checks are current?",
            namespace="demo",
        )


class RuntimeTests(unittest.TestCase):
    def test_missing_key_returns_explicit_preview_without_output(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = OpenAIResponsesAdapter(force_preview=False).respond(sample_packet())
        self.assertTrue(result.preview_only)
        self.assertEqual(result.status, "preview_only")
        self.assertIsNone(result.output_text)
        self.assertFalse(result.request["store"])

    def test_live_boundary_uses_static_instructions_and_captures_receipt(self) -> None:
        response = SimpleNamespace(
            _request_id="req_test",
            id="resp_test",
            model="gpt-5.6-sol-2026-07-01",
            status="completed",
            output_text="Ready.",
            usage=SimpleNamespace(input_tokens=100, output_tokens=3, total_tokens=103),
        )
        fake = FakeResponses(response=response)
        result = OpenAIResponsesAdapter(client=FakeClient(fake)).respond(sample_packet())
        self.assertFalse(result.preview_only)
        self.assertEqual(result.model, "gpt-5.6-sol-2026-07-01")
        self.assertEqual(result.response_id, "resp_test")
        self.assertEqual(result.request_id, "req_test")
        self.assertEqual(result.usage["total_tokens"], 103)
        self.assertIsNotNone(result.observed_at)
        request = fake.requests[0]
        self.assertEqual(request["instructions"], DEVELOPER_INSTRUCTIONS)
        self.assertFalse(request["store"])
        user_text = request["input"][0]["content"][0]["text"]
        user_data = json.loads(user_text)
        self.assertIn("compiled_context", user_data)
        self.assertNotIn(user_data["compiled_context"], DEVELOPER_INSTRUCTIONS)

    def test_provider_errors_do_not_echo_request_contents(self) -> None:
        fake = FakeResponses(error=RuntimeError("secret provider detail"))
        with self.assertRaises(RuntimeCallError) as caught:
            OpenAIResponsesAdapter(client=FakeClient(fake)).respond(sample_packet())
        self.assertNotIn("secret provider detail", str(caught.exception))
        self.assertIn("RuntimeError", str(caught.exception))

    @unittest.skipUnless(importlib.util.find_spec("openai"), "OpenAI extra is not installed")
    def test_official_client_constructs_without_network_and_supports_request_shape(self) -> None:
        adapter = OpenAIResponsesAdapter(api_key="test-" + "only-placeholder")
        client = adapter._get_client()  # noqa: SLF001 - optional SDK compatibility contract
        parameters = inspect.signature(client.responses.create).parameters
        for name in (
            "model",
            "instructions",
            "input",
            "reasoning",
            "max_output_tokens",
            "store",
        ):
            self.assertIn(name, parameters)


class HTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = make_server(port=0, db_path=":memory:")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.server.application.close()

    def request(self, path: str, payload: object | None = None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {} if payload is None else {"Content-Type": "application/json"}
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers)
        return urllib.request.urlopen(request, timeout=5)

    def test_health_seed_compile_and_preview_ask(self) -> None:
        with self.request("/health") as response:
            health = json.load(response)
            self.assertEqual(health["mode"], "preview_only")
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")

        with self.request("/api/seed", {"namespace": "demo"}) as response:
            self.assertTrue(json.load(response)["audit_valid"])

        payload = {
            "namespace": "demo",
            "query": "What release checks are current?",
            "budget_tokens": 500,
            "scopes": ["global"],
        }
        with self.request("/api/compile", payload) as response:
            packet = json.load(response)
            self.assertLessEqual(packet["used_tokens"], packet["budget_tokens"])
        with self.request("/api/ask", {**payload, "preview": True}) as response:
            result = json.load(response)
            self.assertTrue(result["model_run"]["preview_only"])
            self.assertIsNone(result["model_run"]["output_text"])

    def test_request_validation_and_static_path_boundary(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request(
                "/api/ask",
                {"query": "x", "preview": "false", "budget_tokens": 500},
            )
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request("/../pyproject.toml")
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()

    def test_non_loopback_and_live_http_require_explicit_authentication(self) -> None:
        with self.assertRaises(ValueError):
            make_server(host="0.0.0.0", port=0, db_path=":memory:")
        with self.assertRaises(ValueError):
            make_server(
                port=0,
                db_path=":memory:",
                enable_live_http=True,
            )

    def test_bearer_token_protects_post_routes(self) -> None:
        protected = make_server(
            port=0,
            db_path=":memory:",
            auth_token="test-http-token-1234",
        )
        thread = threading.Thread(target=protected.serve_forever, daemon=True)
        thread.start()
        host, port = protected.server_address[:2]
        request = urllib.request.Request(
            f"http://{host}:{port}/api/seed",
            data=b'{"namespace":"demo"}',
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=5)
            self.assertEqual(caught.exception.code, 401)
            caught.exception.close()
        finally:
            protected.shutdown()
            thread.join(timeout=5)
            protected.server_close()
            protected.application.close()


if __name__ == "__main__":
    unittest.main()
