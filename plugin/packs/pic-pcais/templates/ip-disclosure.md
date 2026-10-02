# IP Disclosure — {disclosure.title}

<!-- Routed to the PIC Director of Data and Intellectual Property AS IP ARISES, not on a cadence
     (PIC PM Guide, "IP reporting"): members report "particulars of any new IP developed in the
     project and any new or planned IP commercialization activity" when it happens; anything
     unreported is swept up by the annual questionnaire. Delivery: gmail.draft — a human sends. -->

**Project:** {project.short_name} ({project.pic_number})
**Disclosing member:** {member.organization}
**Date of disclosure:** {disclosure.date}
**To:** PIC Director of Data and Intellectual Property

## Classification

**Type:** {disclosure.ip_type}  *(foreground | background-update | commercialization-activity)*

> Foreground IP: created during the project, in whole or in part using PIC funding — default
> ownership per MPA Schedule. Background IP: owned prior to project start or created independent
> of project funding — member retains ownership, licenses granted per MPA terms.

## Particulars

**Title:** {disclosure.title}
**Contributors / inventors:** {disclosure.inventors}
**Description of the IP:** {disclosure.description}
**Background IP it depends on:** {disclosure.background_dependencies}
**Milestone(s) it arose from:** {disclosure.milestones}

## Commercialization activity (if applicable)

{disclosure.commercialization}
<!-- e.g. new licenses received or granted, patent filings, spinout, first commercial sale —
     the ad-hoc triggers listed in the ip-tracker profile. -->

## Protection status

**Patent status:** {disclosure.patent_status}
**Trade-secret / confidentiality considerations:** {disclosure.confidentiality_notes}

---
*Recorded in the substrate at ip/disclosures/{disclosure.id}.yaml. This disclosure feeds the
project's IP Registry abstract and the annual questionnaire IP section.*
