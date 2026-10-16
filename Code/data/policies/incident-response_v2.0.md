# Incident Response Procedure v2.0
**Effective Date:** September 15, 2025
**Supersedes:** v1.1
**Superseded By:** v2.1 (effective March 1, 2026)

## 1. Purpose
To establish a standardized approach for detecting, responding to, and recovering from cybersecurity incidents, aligned with NIST SP 800-61r2 and ISO 27035.

## 2. Scope
This procedure applies to all employees, contractors, consultants, and third parties with access to company information systems.

## 3. Incident Response Phases

### 3.1 Preparation
- Maintain incident response contact list (updated monthly)
- Ensure backup and recovery procedures are tested weekly
- Conduct quarterly incident response tabletop exercises
- Annual red team/blue team exercises
- Maintain security monitoring tools with 24/7 alerting

### 3.2 Identification
- Potential incidents reported via: security@company.com, ext. 5555, ticketing system, or mobile app
- Initial triage within 5 minutes of report (reduced from 15 minutes)
- Severity levels: 
  * Level 1: Informational (no action required)
  * Level 2: Low (documented, monitored)
  * Level 3: Medium (requires response within 4 hours)
  * Level 4: High (requires response within 1 hour)
  * Level 5: Critical (requires immediate response)
- Evidence preservation: Forensic images, memory dumps, network packets, logs
- Chain of custody documentation for all evidence

### 3.3 Containment
- Short-term: Network segmentation, account disabling, process termination
- Long-term: System rebuild, application patching, access control review
- All containment actions require dual approval for Critical incidents
- Automatic containment enabled for malware detected by EDR

### 3.4 Eradication
- Complete removal of threat artifacts
- Vulnerability remediation within 24 hours for Critical incidents
- Root cause analysis using 5 Whys methodology
- Retesting of controls after eradication

### 3.5 Recovery
- Systems restored from known good backups or rebuilt
- Validation in isolated environment before production return
- Monitoring for 45 days post-recovery (increased from 30)
- Business impact assessment conducted during recovery

### 3.6 Lessons Learned
- Formal incident report completed within 2 business days
- Lessons learned meeting within 5 business days
- Action items tracked in ticketing system with SLA
- Annual review of incident response program effectiveness
- Metrics: MTTD (Mean Time To Detect), MTTR (Mean Time To Respond), MTTC (Mean Time To Contain)

## 4. Roles and Responsibilities
- **Incident Commander (IC)**: Overall authority, makes final decisions
- **Deputy IC**: Assists IC, manages specific aspects
- **Technical Lead**: Oversees technical response efforts
- **Communications Lead**: Internal and external communications
- **Documentation Lead**: Maintains records, chain of custody
- **Legal/Compliance**: Regulatory considerations, evidence handling
- **Business Liaison**: Represents affected business units
- **All Personnel**: Report incidents through designated channels immediately

## 5. Communication Protocol
- Status updates every hour during active incident (increased frequency)
- Executive briefings every 4 hours
- Regulatory notifications per applicable laws (GDPR: 72 hours, CCPA: 30 days)
- Internal breach notification to all employees within 24 hours for Confirmed breaches
- After-action report distributed to board of directors within 30 days

## 6. Metrics and Reporting
- Track: Number of incidents, MTTR, recurrence rate, false positives
- Monthly metrics report to security committee
- Quarterly effectiveness review
- Annual penetration test of IR capabilities

## 7. Revision History
- v1.0: Initial procedure (January 1, 2025)
- v1.1: Added containment timelines and roles clarification (March 15, 2025)
- v2.0: NIST alignment, improved timelines, added metrics (September 15, 2025)