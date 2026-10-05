---
name: project_plan
description: Generate the project plan with goals, milestones, deliverables, and success criteria.
inputs: [plan.txt, strategic_decisions.md, scenarios.md, consolidate_assumptions_short.md, pre_project_assessment.json]
outputs: [project_plan_raw.json, project_plan.md]
tier: low
est_llm_calls: 1
max_words_per_field: 80
max_items_per_list: 5
---
One structured call: system prompt `prompts/system.md`, schema `schema.json` (GoalDefinition:
goal_statement, smart_criteria{specific, measurable, achievable, relevant, time_bound}, dependencies,
resources_required, related_goals, tags, risk_assessment_and_mitigation_strategies{key_risks,
diverse_risks, mitigation_plans}, stakeholder_analysis{primary_stakeholders, secondary_stakeholders,
engagement_strategies}, regulatory_and_compliance_requirements{permits_and_licenses,
compliance_standards, regulatory_bodies, compliance_actions}).
User prompt concatenates plan.txt, strategic_decisions.md, scenarios.md, `assumptions.md`
(= consolidate_assumptions_short.md, as in PlanExe) and `pre-project-assessment.json` (compact JSON).
Markdown: goal statement, then one section per schema group with bullet lists.

Prompt tweak vs PlanExe: the Time-bound instruction ("no specific date unless specified by the user")
adds that a stated current date plus "Project start ASAP" counts as specified, so the timeline is
anchored to it (Sonnet otherwise read the rule literally and gave an undated "~20 years").
