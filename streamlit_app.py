def make_display_label(r: dict) -> str:
    # Safe getters (works even if keys are missing)
    name  = (r.get("rep_name") or r.get("name") or r.get("full_name") or "").strip()
    role  = (r.get("rep_role") or r.get("role") or "").strip()
    dist  = str(r.get("rep_district") or r.get("district") or "").strip()
    party = (r.get("rep_party") or r.get("party") or "").strip()
    email = (r.get("rep_email") or r.get("email") or "").strip()

    parts = [p for p in [name] if p]
    meta = " ".join([p for p in [party, (f"Dist {dist}" if dist else ""), role] if p]).strip()

    if meta:
        parts.append(f"({meta})")
    if email:
        parts.append(f"— {email}")

    return " ".join(parts) if parts else "Unknown Representative"

# Normalize reps so display_label always exists
normalized_reps = []
for i, r in enumerate(reps or []):
    if not isinstance(r, dict):
        # If you somehow have rows/Series/objects, coerce to dict
        try:
            r = dict(r)
        except Exception:
            r = {"_raw": str(r)}
    r["display_label"] = r.get("display_label") or make_display_label(r)
    normalized_reps.append(r)

if not normalized_reps:
    st.error("No representatives found for your selection.")
    st.stop()

labels = [r["display_label"] for r in normalized_reps]
choice_label = st.selectbox("Select Representative", labels)

# Get the chosen rep dict back
choice_idx = labels.index(choice_label)
chosen_rep = normalized_reps[choice_idx]