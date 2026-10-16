# Version-Aware RAG System Specification: IT Security Policy Domain

## 1. Domain Selection
**Chosen Domain**: IT Security Policy
**Rationale**: IT security policies frequently change due to evolving threats, regulatory requirements, and technology updates. Using outdated policies can lead to security vulnerabilities, compliance violations, and operational risks.

## 2. Core Questions the System Must Answer

### Current Policy Queries (Default Behavior)
- What is the current password complexity requirement for employee accounts?
- What are the current procedures for reporting a security incident?
- What data encryption standards are currently mandated for sensitive information?
- What are the current access control principles for privileged accounts?
- What is the current policy regarding personal device usage (BYOD) in the workplace?

### Historical/As-of Queries
- What was the password policy on January 1, 2026? (for audit purposes)
- How did the incident reporting procedure change between Q1 and Q2 2026?
- What data retention requirements were in effect during Q3 2025?
- What were the acceptable use policies for cloud services in March 2026?

### Comparative Queries
- How have data classification levels changed from v2 to v3 of the security policy?
- What additional security controls were added for remote work in the latest version?
- Which encryption algorithms were deprecated between versions?

## 3. What "Wrong" Looks Like

### Primary Risk: Acting on Superseded Policy Information
**Example Scenario**: 
An IT administrator asks: "What is the maximum password age requirement?" 
- **Wrong Answer**: "Passwords must be changed every 90 days" (based on v2.1 policy)
- **Correct Answer**: "Passwords must be changed every 60 days" (current v3.0 policy, effective March 2026)
- **Consequence**: System remains vulnerable to credential-based attacks longer than necessary

### Secondary Risks:
1. **Incomplete Policy Application**: Missing newly added security controls
   - Example: Not implementing multi-factor authentication for admin consoles because the administrator consulted v2.0 which didn't require it

2. **Compliance Violations**: Following outdated regulatory requirements
   - Example: Applying GDPR data retention periods that have been superseded by newer CCPA requirements

3. **Operational Inefficiency**: Using decommissioned procedures
   - Example: Following an outdated incident escalation path that no longer reflects current team structure

4. **Security Gaps**: Relying on revoked permissions or protocols
   - Example: Allowing TLS 1.0 for internal communications because the administrator read an archived version that permitted it

### Detection Mechanism:
The system should flag answers that:
- Contain information from a superseded policy version without explicit user request for historical data
- Fail to reference the effective date of the policy version being cited
- Contradict information found in the current version of the same policy document

## 4. Version Metadata Requirements
For each IT security policy document, the system must track:
- `doc_id`: e.g., "it-security-policy", "password-standards", "incident-response-procedure"
- `version`: Semantic versioning (v1.0, v2.1, v3.0) or date-based (2026-Q1, 2026-Q2)
- `effective_from`: Date when this version becomes active
- `effective_to`: Date when this version is superseded (null for current)
- `status`: current/superseded/draft/archived
- `supersedes`: Previous version ID that this version replaces

## 5. Success Metrics
- **Current-version accuracy**: >95% of default queries answered from current policy version
- **Stale-answer reduction**: <2% of responses contain outdated policy information (vs. estimated 30%+ in baseline RAG)
- **Version attribution**: 100% of answers correctly cite the policy version and effective date
- **User trust**: Security personnel can reliably use the system for policy verification without cross-checking source documents

## 6. Implementation Notes for This Domain
- Policies often contain version numbers in headers/footers that can be automatically extracted
- Effective dates are typically found in revision history sections
- Changes often involve: updated technical standards, changed timeframes, added/removed procedures, revised role responsibilities
- Contradictions to plant: conflicting password requirements, differing incident reporting timelines, varying access control principles