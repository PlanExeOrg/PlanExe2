import re
import time

from planexe_skill.planexe import planexe_metadata, structured

TARGET_CANDIDATES = 9
BATCH_SIZE = 3
MAX_CALLS = 3
PURPOSE_LABEL_KEYS = {"personal", "business", "public_good", "other"}
_WS = re.compile(r"\s+")


def normalize_label(label: str) -> str:
    return _WS.sub(" ", label).strip()


def label_key(label: str) -> str:
    return normalize_label(label).casefold()


def augment_with_context(prompt: str, purpose_md: str, constraints_md: str) -> str:
    sections = [prompt]
    if purpose_md.strip():
        sections.append("## Plan purpose (auto-derived; for context only)\n" + purpose_md.strip())
    if constraints_md.strip():
        sections.append("## Extracted constraints (auto-derived; for context only)\n" + constraints_md.strip())
    if len(sections) == 1:
        return prompt
    return "\n\n---\n\n".join(sections) + "\n"


def derive_primary(fits: list[dict]) -> str:
    if not fits:
        return "Unclear"
    key = lambda f: (-(f["importance"] * f["specificity"]), -f["specificity"], -f["importance"])
    outcome = [f for f in fits if f["role"] == "outcome"]
    return normalize_label(sorted(outcome or fits, key=key)[0]["domain"])


def derive_secondaries(fits: list[dict], primary: str, cap: int = 3) -> list[str]:
    seen = {label_key(primary)}
    out = []
    for f in fits:
        domain = normalize_label(f["domain"])
        key = label_key(domain)
        if not domain or key in seen:
            continue
        seen.add(key)
        out.append(domain)
        if len(out) >= cap:
            break
    return out


def format_candidate_list(fits: list[dict]) -> str:
    lines = [f"There are {len(fits)} candidate domains. Pick one.", ""]
    for i, f in enumerate(fits):
        lines.append(f"- `[{i}]` domain={f['domain']!r}, importance={f['importance']}, "
                     f"specificity={f['specificity']}, role={f['role']!r}, reason={f['reason']!r}")
    return "\n".join(lines)


def to_markdown(primary: str, secondaries: list[str], rationale: str, fits: list[dict]) -> str:
    lines = [f"**Primary domain:** {primary}", "",
             f"**Secondary domains:** {', '.join(secondaries) if secondaries else '_(none)_'}", "",
             f"**Rationale:** {rationale}"]
    if fits:
        lines += ["", "**Disciplines this project involves:**", "",
                  "| Domain | Importance | Specificity | Role | Reason |", "|---|---|---|---|---|"]
        for f in sorted(fits, key=lambda f: -(f["importance"] * f["specificity"])):
            reason = f["reason"].replace("|", "\\|")
            lines.append(f"| {f['domain']} | {f['importance']} | {f['specificity']} | {f['role']} | {reason} |")
    return "\n".join(lines)


def run(ctx):
    plan = ctx.read_text("plan.txt")
    purpose = str(ctx.read_json("identify_purpose_raw.json").get("purpose", "") or "").strip().lower()
    user_prompt = augment_with_context(plan, ctx.read_text("identify_purpose.md"),
                                       ctx.read_text("extract_constraints.md"))
    system_prompt = ctx.skill_file(
        f"prompts/system_{purpose if purpose in PURPOSE_LABEL_KEYS else 'business'}.md").strip()
    fits_schema = ctx.skill_json("schema_fits.json")

    fits: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []
    first_pass_seconds = 0.0
    last_result = None
    calls = 0
    for call_index in range(1, MAX_CALLS + 1):
        if call_index == 1:
            user_msg = user_prompt
        else:
            names = ", ".join(f'"{f["domain"]}"' for f in fits)
            user_msg = (f"You have already produced these candidate domains in earlier batches: [{names}].\n"
                        f"Produce {BATCH_SIZE} MORE candidate expert disciplines for the project below — distinct "
                        f"disciplines that are also relevant to this project but were not yet listed.\n\n"
                        f"{user_prompt}")
        t = time.time()
        try:
            response, last_result = structured(ctx, system_prompt, user_msg, fits_schema, label=f"batch {call_index}")
        except Exception as e:
            if call_index == 1 and not fits:
                raise
            warnings.append(f"First-pass batch {call_index} failed ({type(e).__name__}: {e}); "
                            f"continuing with {len(fits)} candidate(s).")
            continue
        first_pass_seconds += time.time() - t
        calls += 1
        batch = response.get("domain_fits") or []
        if call_index == 1 and not batch:
            break
        before = len(fits)
        for f in batch:
            domain = normalize_label(str(f.get("domain", "")))
            if not domain:
                warnings.append("Dropped fit with empty domain label.")
                continue
            key = label_key(domain)
            if key in PURPOSE_LABEL_KEYS:
                warnings.append(f"Dropped purpose-tag fit (purpose belongs in the purpose field, not the "
                                f"candidate list): {domain}")
                continue
            if key in seen:
                warnings.append(f"Dropped duplicate fit domain: {domain}")
                continue
            imp = max(1, min(5, int(f["importance"])))
            spec = max(1, min(5, int(f["specificity"])))
            if imp != f["importance"] or spec != f["specificity"]:
                warnings.append(f"Clamped out-of-range Likert score for {domain}: importance {f['importance']} -> "
                                f"{imp}, specificity {f['specificity']} -> {spec}.")
            if imp == 1 and spec == 1:
                warnings.append(f"Dropped 1×1 candidate (importance=1 and specificity=1, effectively unrelated): {domain}")
                continue
            if len(fits) >= TARGET_CANDIDATES:
                warnings.append(f"Truncated extra fit beyond cap of {TARGET_CANDIDATES}: {domain}")
                continue
            seen.add(key)
            fits.append({"domain": domain, "importance": imp, "specificity": spec, "role": f["role"],
                         "reason": normalize_label(str(f.get("reason", "")))})
        added = len(fits) - before
        if len(fits) >= TARGET_CANDIDATES:
            break
        if added == 0 and call_index > 1:
            warnings.append(f"First-pass batch {call_index} added 0 new candidates (all duplicates or rejected); "
                            f"stopping loop with {len(fits)} candidate(s).")
            break
    if fits and len(fits) < TARGET_CANDIDATES:
        warnings.append(f"First-pass produced {len(fits)} candidate(s) after {calls} batch call(s); "
                        f"target was {TARGET_CANDIDATES}.")

    primary_select_seconds = 0.0
    if not fits:
        primary = "Unclear"
        rationale = "No candidates emitted; the prompt is too vague to identify a project."
    else:
        t = time.time()
        purpose_section = f"## Project purpose\n\n{purpose}\n\n---\n\n" if purpose in PURPOSE_LABEL_KEYS else ""
        sel_msg = f"{user_prompt}\n\n---\n\n{purpose_section}## Candidate domains\n{format_candidate_list(fits)}\n"
        try:
            sel, _ = structured(ctx, ctx.skill_file("prompts/primary_select.md").strip(), sel_msg,
                                ctx.skill_json("schema_primary.json"), label="primary select")
            idx = int(sel["primary_index"])
            if idx < 0 or idx >= len(fits):
                raise IndexError(f"Primary-selection index {idx} out of range [0, {len(fits)}).")
            primary = normalize_label(fits[idx]["domain"])
            rationale = normalize_label(sel["rationale"])
        except Exception as exc:
            fallback = derive_primary(fits)
            warnings.append(f"Primary-selection LLM call failed ({type(exc).__name__}: {exc}); falling back to "
                            f"derive_primary -> {fallback!r}.")
            primary = fallback
            rationale = ("Second-pass selection failed; primary derived from the priority-chain fallback "
                         "(high+outcome > medium+outcome > high any role > Unclear).")
        primary_select_seconds = round(time.time() - t, 3)

    secondaries = derive_secondaries(fits, primary)
    meta = planexe_metadata(last_result) if last_result else {}
    meta.pop("duration", None)
    meta["duration_seconds"] = round(first_pass_seconds, 3)
    meta["first_pass_call_count"] = calls
    meta["first_pass_candidate_count"] = len(fits)
    if primary_select_seconds:
        meta["primary_select_duration_seconds"] = primary_select_seconds
    raw = {"primary_domain": primary, "secondary_domains": secondaries, "domain_fits": fits,
           "rationale": rationale, "warnings": warnings, "metadata": meta,
           "system_prompt": system_prompt, "user_prompt": user_prompt}
    ctx.write_json("classify_domain_raw.json", raw)
    ctx.write_text("classify_domain.md", to_markdown(primary, secondaries, rationale, fits))
