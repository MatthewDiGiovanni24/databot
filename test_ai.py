"""Offline checks for report capture and Gemini analysis delivery."""

import base64
from datetime import datetime, timezone
from email.utils import format_datetime
from io import BytesIO
import json
import os
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import ai


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        jitter = patch("ai.random.uniform", return_value=0.25)
        jitter.start()
        self.addCleanup(jitter.stop)

    @patch("ai.time.sleep")
    @patch("ai.urlopen")
    def test_transient_failure_retries_then_uses_fallback(self, urlopen, sleep):
        success = Mock()
        success.__enter__ = Mock(return_value=BytesIO(b'{"candidates": []}'))
        success.__exit__ = Mock(return_value=False)
        urlopen.side_effect = [
            HTTPError("url", 503, "Unavailable", {}, None),
            TimeoutError(), success,
        ]
        result = ai.request_analysis({}, "secret", "primary", "backup")
        self.assertEqual(result, {"candidates": []})
        urls = [call.args[0].full_url for call in urlopen.call_args_list]
        self.assertIn("primary:generateContent", urls[0])
        self.assertIn("primary:generateContent", urls[1])
        self.assertIn("backup:generateContent", urls[2])
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [5.25, 10.25])
        self.assertTrue(all(call.kwargs["timeout"] == 60 for call in urlopen.call_args_list))

    @patch("ai.time.sleep")
    @patch("ai.urlopen", side_effect=URLError("private network details"))
    def test_connection_retries_are_bounded_and_sanitized(self, urlopen, sleep):
        with self.assertRaisesRegex(ai.AnalysisError, "after 5 attempts") as error:
            ai.request_analysis({}, "secret", "primary", "backup")
        self.assertNotIn("private", str(error.exception))
        self.assertEqual(urlopen.call_count, 5)
        self.assertEqual(sleep.call_count, 4)

    @patch("ai.time.sleep")
    @patch("ai.urlopen", side_effect=HTTPError("url", 429, "Rate limit", {"Retry-After": "8"}, None))
    def test_rate_limit_respects_retry_after(self, urlopen, sleep):
        with self.assertRaises(ai.AnalysisError):
            ai.request_analysis({}, "secret", "primary", "")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [8.25, 10.25, 20.25, 30.25])
        self.assertTrue(all("primary:generateContent" in call.args[0].full_url
                            for call in urlopen.call_args_list))

    @patch("ai.time.sleep")
    @patch("ai.urlopen", side_effect=HTTPError("url", 403, "Forbidden", {}, None))
    def test_auth_errors_are_not_retried(self, urlopen, sleep):
        with self.assertRaisesRegex(ai.AnalysisError, "HTTP 403"):
            ai.request_analysis({}, "secret", "primary", "backup")
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch("builtins.print")
    @patch("ai.time.sleep")
    @patch("ai.urlopen", side_effect=HTTPError("private-url", 503, "private-body", {}, None))
    def test_five_attempt_schedule_and_safe_logs(self, urlopen, sleep, log):
        with self.assertRaises(ai.AnalysisError):
            ai.request_analysis({"report": "private-report"}, "private-key", "primary", "backup")
        models = [call.args[0].full_url.split("/models/")[1].split(":")[0]
                  for call in urlopen.call_args_list]
        self.assertEqual(models, ["primary", "primary", "backup", "backup", "backup"])
        self.assertEqual([call.args[0] for call in sleep.call_args_list],
                         [5.25, 10.25, 20.25, 30.25])
        self.assertEqual(log.call_count, 5)
        for index, call in enumerate(log.call_args_list):
            text = call.args[0]
            self.assertIn(f"model={models[index]}", text)
            self.assertIn(f"attempt={index + 1}/5", text)
            self.assertIn("http_status=503", text)
            self.assertIn("retry_delay=", text)
            self.assertNotIn("private", text)

    @patch("ai.time.sleep")
    @patch("ai.urlopen")
    def test_retry_after_seconds_dates_and_invalid_values(self, urlopen, sleep):
        now = 1800000000
        future_date = format_datetime(datetime.fromtimestamp(now + 120, timezone.utc), usegmt=True)
        past_date = format_datetime(datetime.fromtimestamp(now - 120, timezone.utc), usegmt=True)
        for header, first_delay in [("90", 90.25), (future_date, 120.25),
                                    (past_date, 5.25), ("invalid", 5.25),
                                    ("NaN", 5.25), ("-1", 5.25)]:
            with self.subTest(header=header), patch("ai.time.time", return_value=now):
                sleep.reset_mock()
                success = Mock()
                success.__enter__ = Mock(return_value=BytesIO(b'{}'))
                success.__exit__ = Mock(return_value=False)
                urlopen.side_effect = [HTTPError("url", 503, "Unavailable",
                                               {"Retry-After": header}, None), success]
                self.assertEqual(ai.request_analysis({}, "secret", "primary", "backup"), {})
                sleep.assert_called_once_with(first_delay)

    def test_capture_preserves_upload_and_excludes_failed_sends(self):
        client = Mock()
        report = ai.ReportClient(client, "dc")
        report.chat_postMessage(channel="dc", text="Missing brake temperature")
        report.chat_postMessage(channel="other", text="Another report")
        with BytesIO(b"graph bytes") as image:
            report.files_upload_v2(channel="dc", file=image, title="Front pressure")
        self.assertEqual(report.messages, ["Missing brake temperature"])
        self.assertEqual(report.graphs, [("Front pressure", b"graph bytes")])
        client.chat_postMessage.side_effect = RuntimeError("upload failed")
        with self.assertRaises(RuntimeError):
            report.chat_postMessage(channel="dc", text="Not sent")
        self.assertEqual(len(report.messages), 1)
        client.files_upload_v2.side_effect = RuntimeError("upload failed")
        with self.assertRaises(RuntimeError), BytesIO(b"failed") as image:
            report.files_upload_v2(channel="dc", file=image, title="Not sent")
        self.assertEqual(len(report.graphs), 1)

    @patch("ai.load_dotenv")
    @patch.dict(os.environ, {"API_KEY": "test-secret", "GEMINI_MODEL": "test-model"})
    @patch("ai.urlopen")
    def test_request_contains_every_message_and_graph(self, urlopen, dotenv):
        response = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"text": "Hidden reasoning", "thought": True}, {"text": "Brief analysis"},
        ]}}]}
        urlopen.return_value.__enter__.return_value = BytesIO(json.dumps(response).encode())
        result = ai.analyze_report(["Report heading", "Fault count: 1"],
                                   [("Front", b"front"), ("Rear", b"rear")])
        self.assertEqual(result, "Brief analysis")
        request = urlopen.call_args.args[0]
        self.assertNotIn("test-secret", request.full_url)
        parts = json.loads(request.data)["contents"][0]["parts"]
        self.assertIn("Fault count: 1", parts[0]["text"])
        self.assertIn("Report heading", parts[0]["text"])
        images = [base64.b64decode(p["inlineData"]["data"]) for p in parts if "inlineData" in p]
        self.assertEqual(images, [b"front", b"rear"])

    @patch("ai.analyze_report", return_value="Pressure rises during braking.")
    def test_analysis_posts_after_report_without_recapturing_it(self, analyze):
        client = Mock()
        report = ai.ReportClient(client, "dc")
        report.chat_postMessage(channel="dc", text="DC Report")
        ai.send_report_analysis(report)
        self.assertEqual(client.chat_postMessage.call_count, 2)
        self.assertEqual(report.messages, ["DC Report"])
        self.assertEqual(client.chat_postMessage.call_args.kwargs["channel"], "dc")
        self.assertIn("Pressure rises", client.chat_postMessage.call_args.kwargs["text"])
        other = ai.ReportClient(client, "electrical")
        self.assertEqual(other.messages, [])
        self.assertEqual(other.graphs, [])

    @patch("builtins.print")
    @patch("ai.analyze_report", side_effect=ai.AnalysisError("Gemini request failed (HTTP 429)."))
    def test_analysis_failure_does_not_post_or_raise(self, analyze, log):
        client = Mock()
        ai.send_report_analysis(ai.ReportClient(client, "dc"))
        client.chat_postMessage.assert_not_called()
        self.assertIn("429", log.call_args.args[0])

    @patch("ai.load_dotenv")
    @patch.dict(os.environ, {"API_KEY": "test-secret"})
    @patch("ai.urlopen", side_effect=HTTPError("url", 403, "secret remote error", {}, None))
    def test_remote_errors_are_sanitized(self, urlopen, dotenv):
        with self.assertRaisesRegex(ai.AnalysisError, r"HTTP 403") as error:
            ai.analyze_report(["Report"], [])
        self.assertNotIn("secret", str(error.exception))

    @patch("ai.load_dotenv")
    @patch.dict(os.environ, {"API_KEY": ""})
    @patch("ai.urlopen")
    def test_missing_key_does_not_call_api(self, urlopen, dotenv):
        with self.assertRaisesRegex(ai.AnalysisError, "Set API_KEY"):
            ai.analyze_report(["Report"], [])
        urlopen.assert_not_called()

    @patch("ai.load_dotenv")
    @patch.dict(os.environ, {"API_KEY": "test-secret"})
    @patch("ai.urlopen")
    def test_incomplete_response_is_not_posted_as_analysis(self, urlopen, dotenv):
        response = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {
            "parts": [{"text": "Incomplete analysis"}],
        }}]}
        urlopen.return_value.__enter__.return_value = BytesIO(json.dumps(response).encode())
        with self.assertRaisesRegex(ai.AnalysisError, "complete analysis"):
            ai.analyze_report(["Report"], [])

    def test_bot_analyzes_each_report_before_starting_next(self):
        import bot
        import pandas as pd

        events = []
        client = Mock()
        client.chat_postMessage.side_effect = lambda **kwargs: events.append(
            (kwargs["channel"], kwargs["text"]))

        def report(df, report_client, channel):
            report_client.chat_postMessage(channel=channel, text="Report")
            with BytesIO(b"png") as image:
                report_client.files_upload_v2(channel=channel, file=image, title="Graph")

        def analyze(messages, graphs):
            self.assertEqual(messages, ["Report"])
            self.assertEqual(graphs, [("Graph", b"png")])
            return "Analysis"

        channels = {"ELECTRICAL_CHANNEL": "electrical", "CHASSIS_CHANNEL": "chassis",
                    "POWER_TRAIN_CHANNEL": "powertrain", "DC_CHANNEL": "dc", "SLACK_TOKEN": "test"}
        with patch.dict(os.environ, channels), patch("bot.load_dotenv"), \
                patch("bot.WebClient", return_value=client), \
                patch("bot.read_motec_csv", return_value=pd.DataFrame()), \
                patch("bot.Path.exists", return_value=True), \
                patch.multiple("bot", send_electrical_report=report,
                               send_chassis_report=report, send_power_train_report=report,
                               send_dc_report=report), \
                patch("ai.analyze_report", side_effect=analyze), patch("builtins.print"):
            bot.main()
            successful_events = list(events)
            events.clear()
            with patch("ai.analyze_report", side_effect=ai.AnalysisError("Gemini unavailable")):
                bot.main()
            self.assertEqual(events, [(channel, "Report") for channel in
                                     ("electrical", "chassis", "powertrain", "dc")])
            events = successful_events
        self.assertEqual(events, [event for channel in
                         ("electrical", "chassis", "powertrain", "dc")
                         for event in [(channel, "Report"),
                                       (channel, "*AI report analysis*\nAnalysis")]])


if __name__ == "__main__":
    unittest.main()
