# Annual Questionnaire — IP Section — {project.short_name} {year}

<!-- The annual questionnaire is the catch-all: "any previously unreported IP or commercialization
     activity is captured in the annual questionnaire" (PM Guide, "IP reporting"). This section is
     assembled from the substrate records the ip-tracker profile names as inputs_drawn_from —
     it summarizes what is already on file and surfaces what was never disclosed in-year. -->

**Member:** {member.organization} · **Reporting year:** {year}

## 1. Foreground IP recognized this year

<!-- from ip/disclosures/*.yaml -->
{foreground_ip_table}

## 2. Previously unreported IP or commercialization activity

<!-- Anything surfacing here is a capture gap — it should have been disclosed as it arose. -->
{unreported_items}

## 3. IP rationale — status against plan

<!-- from ip/rationale.md; significant changes to the IP Rationale require a formal Change Order
     whether or not there is a budgetary implication (PM Guide). -->
{rationale_status}

## 4. Licenses

**Granted:** {licenses_granted_summary}   <!-- from ip/licenses-granted.yaml -->
**Received:** {licenses_received_summary} <!-- from ip/licenses-received.yaml -->

## 5. Commercialization status

<!-- from ip/commercialization-status.yaml -->
{commercialization_status}

---
*Drafted from substrate records; reviewed by {project_lead.name} before submission.*
