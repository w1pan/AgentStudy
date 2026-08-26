import os
import unittest
from unittest.mock import MagicMock, patch

from app.nutrition_agent import NutritionEvidenceTarget, resolve_nutrition_evidence
from app.nutrition_search import WebDensityEstimate


class NutritionEvidenceAgentTests(unittest.TestCase):
    def setUp(self):
        self.target = NutritionEvidenceTarget(
            food_name="咖喱鸡预制菜",
            category="mixed_dish",
            kcal_per_100g=165,
            uncertainty_pct=0.28,
            source_name="轻衡分类兜底",
        )
        self.web_estimate = WebDensityEstimate(
            kcal_per_100g=180,
            uncertainty_pct=0.18,
            sample_count=3,
            source_name="DashScope 联网检索同类预制菜",
            source_version="qwen-test/web-test",
        )

    def _agent_that_calls_tools(self, *, search_before_inspection: bool = False):
        captured = {}

        def create(**kwargs):
            captured.update(kwargs)
            tools = {item.name: item for item in kwargs["tools"]}
            agent = MagicMock()

            def invoke(*_args, **_kwargs):
                if search_before_inspection:
                    tools["search_prepared_food_density"].invoke({
                        "targets": [{
                            "food_name": "咖喱鸡预制菜",
                            "category": "mixed_dish",
                        }],
                    })
                    tools["inspect_existing_density_evidence"].invoke({
                        "food_names": ["咖喱鸡预制菜"],
                    })
                else:
                    tools["inspect_existing_density_evidence"].invoke({
                        "food_names": ["咖喱鸡预制菜"],
                    })
                    tools["search_prepared_food_density"].invoke({
                        "targets": [{
                            "food_name": "咖喱鸡预制菜",
                            "category": "mixed_dish",
                        }],
                    })
                return {"messages": []}

            agent.invoke.side_effect = invoke
            return agent

        return captured, create

    def test_agent_inspects_then_searches_with_read_only_tools(self):
        captured, create = self._agent_that_calls_tools()
        with (
            patch.dict(os.environ, {
                "NUTRITION_REACT_ENABLED": "true",
                "NUTRITION_REACT_MODEL": "qwen-react-test",
            }, clear=False),
            patch("app.nutrition_agent.create_agent", side_effect=create),
            patch("app.nutrition_agent._chat_model", return_value=MagicMock()),
            patch(
                "app.nutrition_agent.search_low_confidence_densities",
                return_value={"咖喱鸡预制菜": self.web_estimate},
            ) as search,
        ):
            result = resolve_nutrition_evidence([self.target])

        self.assertEqual(result["咖喱鸡预制菜"], self.web_estimate)
        self.assertEqual(
            [item.name for item in captured["tools"]],
            ["inspect_existing_density_evidence", "search_prepared_food_density"],
        )
        self.assertEqual(captured["name"], "qingheng_nutrition_evidence_agent")
        search.assert_called_once_with([("咖喱鸡预制菜", "mixed_dish")])

    def test_web_tool_rejects_food_that_was_not_inspected_first(self):
        _, create = self._agent_that_calls_tools(search_before_inspection=True)
        with (
            patch.dict(os.environ, {"NUTRITION_REACT_ENABLED": "true"}, clear=False),
            patch("app.nutrition_agent.create_agent", side_effect=create),
            patch("app.nutrition_agent._chat_model", return_value=MagicMock()),
            patch("app.nutrition_agent.search_low_confidence_densities") as search,
        ):
            result = resolve_nutrition_evidence([self.target])

        self.assertEqual(result, {})
        search.assert_not_called()

    def test_agent_failure_falls_back_to_previous_deterministic_search(self):
        failed_agent = MagicMock()
        failed_agent.invoke.side_effect = RuntimeError("tool calling unavailable")
        with (
            patch.dict(os.environ, {"NUTRITION_REACT_ENABLED": "true"}, clear=False),
            patch("app.nutrition_agent.create_agent", return_value=failed_agent),
            patch("app.nutrition_agent._chat_model", return_value=MagicMock()),
            patch(
                "app.nutrition_agent.search_low_confidence_densities",
                return_value={"咖喱鸡预制菜": self.web_estimate},
            ) as search,
        ):
            result = resolve_nutrition_evidence([self.target])

        self.assertEqual(result["咖喱鸡预制菜"], self.web_estimate)
        search.assert_called_once_with([("咖喱鸡预制菜", "mixed_dish")])

    def test_disabled_agent_keeps_previous_direct_search_path(self):
        with (
            patch.dict(os.environ, {"NUTRITION_REACT_ENABLED": "false"}, clear=False),
            patch("app.nutrition_agent.create_agent") as create,
            patch(
                "app.nutrition_agent.search_low_confidence_densities",
                return_value={"咖喱鸡预制菜": self.web_estimate},
            ),
        ):
            result = resolve_nutrition_evidence([self.target])

        self.assertEqual(result["咖喱鸡预制菜"], self.web_estimate)
        create.assert_not_called()

    def test_server_rejects_agent_evidence_that_does_not_improve_uncertainty(self):
        weak = WebDensityEstimate(
            kcal_per_100g=180,
            uncertainty_pct=0.24,
            sample_count=2,
            source_name="DashScope 联网检索同类预制菜",
            source_version="qwen-test/web-test",
        )
        already_better = NutritionEvidenceTarget(
            **{**self.target.__dict__, "uncertainty_pct": 0.22},
        )
        with (
            patch.dict(os.environ, {"NUTRITION_REACT_ENABLED": "false"}, clear=False),
            patch(
                "app.nutrition_agent.search_low_confidence_densities",
                return_value={"咖喱鸡预制菜": weak},
            ),
        ):
            result = resolve_nutrition_evidence([already_better])

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
