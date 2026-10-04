from planexe_skill.shared.team import enrich


def run(ctx):
    enrich(ctx, "enrich_team_members_contract_type.json", "enrich_team_members_background_story_raw.json", "enrich_team_members_background_story.json",
           {"typical_job_activities": "typical_job_activities", "background_story": "job_background_story_of_employee"})
