# Incident Response Procedure v2.1
**Effective Date:** March 1, 2026
**Supersedes:** v2.0
**Superseded By:** None (current)

## 1. Purpose
To establish a standardized approach for detecting, responding to, and recovering from cybersecurity incidents, incorporating lessons learned from recent threat landscape changes.

## 2. Scope
This procedure applies to all employees, contractors, consultants, third parties, and service accounts with access to company information systems.

## 3. Incident Response Phases

### 3.1 Preparation
- Maintain incident response contact list (updated weekly)
- Ensure backup and recovery procedures are tested weekly
- Conduct monthly incident response tabletop exercises (increased from quarterly)
- Annual red team/blue team exercises plus bi-annual purple team exercises
- Continuous monitoring of security tools with automated alert escalation

### 3.2 Identification
- Potential incidents reported via: security@company.com, ext. 5555, ticketing system, mobile app, or SIEM auto-creation
- Initial triage within 2 minutes of report (reduced from 5 minutes)
- Severity levels maintained but with updated response SLAs:
  * Level 1: Informational (logged, no action)
  * Level 2: Low (response within 8 hours)
  * Level 3: Medium (response within 2 hours) 
  * Level 4: High (response within 30 minutes)
  * Level 5: Critical (response within 5 minutes)
- Evidence preservation: Automated collection where possible, manual for complex cases
- Chain of custody: Blockchain-based evidence tracking system implemented

### 3.3 Containment
- Short-term: Automated isolation via SOAR playbooks, account disabling
- Long-term: Golden image restoration, zero-trust network segmentation
- Automatic containment enabled for all confirmed malicious activity
- Manual override available but requires dual approval and justification

### 3.4 Eradication
- Complete removal using automated scripts where possible
- Vulnerability remediation: Critical within 4 hours, High within 24 hours
- Root cause analysis: Preliminary within 2 hours, detailed within 24 hours
- Validation of eradication through continuous monitoring

### 3.5 Recovery
- Systems restored from immutable backups or rebuilt from gold images
- Validation includes security scanning and user acceptance testing
- Monitoring for 60 days post-recovery (increased from 45 days)
- Business continuity validation during recovery process

### 3.6 Lessons Learned
- Preliminary incident report within 1 business day
- Formal report and meeting within 3 business days (accelerated from v2.0)
- Action items assigned with automatic escalation if not completed
- Monthly IR effectiveness review with metrics trending
- Adoption of MITRE ATT&CK framework for technique tracking

## 4. Roles and Responsibilities
- **Incident Commander (IC)**: Single point of authority during incident
- **Technical Operations Lead**: Manals technical response activities
- **Information Security Lead**: Ensures compliance with policies and regulations
- **Communications Lead**: Manages all internal and external messaging
- **Legal and Compliance Lead**: Handles regulatory notifications and evidence
- **Business Impact Lead**: Assesses and communicates business consequences
- **All Personnel**: Must report suspected incidents within 5 minutes of discovery (NEW REQUIREMENT)
- **Automated Systems**: Can initiate IR process without human intervention for certain threats

## 5. Communication Protocol
- Real-time status dashboard available to stakeholders
- Hourly updates during active incident via automated notifications
- Executive briefings every 2 hours during Critical incidents
- Regulatory notifications: As required by law, with attempt to notify within 24 hours where possible
- Internal notification: Secure alert sent to all employees for incidents affecting PII
- Post-incident review: Shared with entire organization for transparency (increased sharing)

## 6. Metrics and Reporting
- Enhanced metrics: 
  * MTTD: Target < 5 minutes
  * MTTR: Target < 2 hours for Medium incidents
  * MTTC: Target < 30 minutes for High incidents
  * percentage of incidents with automated response initiation
  * mean time to notify affected parties
- Real-time metrics dashboard
- Continuous improvement based on metrics analysis
- Annual third-party assessment of IR capabilities

## 7. Revision History
- v1.0: Initial procedure (January 1, 2025)
- v1.1: Added containment timelines and roles clarification (March 15, 2025)
- v2.0: NIST alignment, improved timelines, added metrics (September 15, 2025)
- v2.1: Response time improvements, automation enhancements, stricter reporting (March 1, 2026)