# Data Classification Policy v2.0
**Effective Date:** September 1, 2025
**Supersedes:** v1.0
**Superseded By:** None (current)

## 1. Purpose
To establish a comprehensive framework for classifying company data based on sensitivity, regulatory requirements, and business impact to ensure appropriate protection measures are applied consistently across the organization.

## 2. Scope
This policy applies to all data created, collected, processed, stored, or transmitted by the company, including data held by third parties on behalf of the company, regardless of format, location, or processing method.

## 3. Data Classification Levels

### 3.1 Public Data
- Definition: Information that is lawfully available to the general public from federal, state, or local government records
- Examples: Press releases, published financial statements, job postings, public website content
- Protection: Reasonable controls to prevent unauthorized modification; integrity protection recommended
- Handling: May be freely shared, distributed, or published without restriction

### 3.2 Internal Data
- Definition: Information intended for company use that is not sensitive but should not be unnecessarily disclosed
- Examples: Internal directories, policy documents, procedural manuals, organizational announcements
- Protection: Basic access controls (user authentication required); encryption not required for storage
- Handling: Share within company only; external sharing requires manager approval

### 3.3 Confidential Data
- Definition: Information whose unauthorized disclosure could reasonably be expected to cause measurable harm to the company, employees, or customers
- Examples: Employee personnel records, customer lists, proprietary methodologies, internal financial reports
- Protection: Strong access controls (role-based); encryption required for transmission and recommended for storage
- Handling: Strict need-to-know basis; confidentiality agreements required for third-party access
- Retention: As per business and regulatory requirements

### 3.4 Restricted Data (Sensitive)
- Definition: Information whose unauthorized disclosure could cause severe harm, including legal penalties, significant financial loss, or irreparable reputation damage
- Examples: Trade secrets, encryption keys, merger/acquisition negotiations, security vulnerability details
- Protection: Maximum controls including segregation of duties, multi-factor authentication, encryption at rest and in transit, DLP, IRM
- Handling: Limited to specifically authorized individuals; detailed usage logging and monitoring
- Retention: Minimum necessary to fulfill business/legal requirements; secure destruction required

### 3.5 Special Categories (Regulated Data)
- Definition: Data subject to specific regulatory requirements that dictate handling, retention, and protection
- Examples: 
  * PII (Personally Identifiable Information) under GDPR/CCPA
  * PHI (Protected Health Information) under HIPAA
  * Financial data under PCI-DSS, SOX
  * Export-controlled information under EAR/ITAR
- Protection: As required by applicable regulations, which may exceed Restricted level controls
- Handling: As required by applicable regulations; specialized training may be required
- Retention: As required by applicable regulations

## 4. Classification Responsibilities
- **Data Owner**: Accountable for assessing and classifying data under their authority; reviews classification annually
- **Data Custodian**: Responsible for implementing and maintaining security controls for data in their care
- **Data Steward**: Assists with classification efforts, maintains classification registers, provides guidance
- **All Employees**: Must classify data they create or handle according to this policy; must complete annual training
- **Information Security Team**: Maintains classification framework, provides tools and guidance, handles exceptions

## 5. Data Handling Requirements

### 5.1 Storage
- Public: Company-approved systems with basic access controls
- Internal: Company-approved systems with user authentication
- Confidential: Access-controlled systems with logging; encryption recommended for storage
- Restricted: Encrypted storage with access logging; limited retention; air-gapped for highly sensitive subsets
- Special Categories: As required by applicable regulations

### 5.2 Transmission
- Public: No encryption required for integrity protection
- Internal: Company network acceptable; encryption recommended for wireless transmission
- Confidential: Encryption required for all transmission outside trusted network
- Restricted: Encryption required for all transmission; approved secure channels only (SFTP, HTTPS, encrypted email)
- Special Categories: As required by applicable regulations

### 5.3 Transmission to Third Parties
- Public: No restrictions
- Internal: Requires NDA or data processing agreement
- Confidential: Requires NDA and specific data handling commitments
- Restricted: Requires explicit approval and comprehensive data protection agreement
- Special Categories: As required by applicable regulations and data processing agreements

### 5.4 Destruction and Disposal
- All data must be destroyed according to documented retention schedules
- Public and Internal: Standard deletion procedures acceptable
- Confidential: Secure deletion methods (cryptographic wiping, physical destruction of media)
- Restricted and Special Categories: Physical destruction or certified cryptographic wiping required
- Certification of destruction required for all Confidential, Restricted, and Special Categories media

## 6. Data Classification Process
1. Inventory: Identify data elements and repositories
2. Assessment: Evaluate sensitivity, regulatory requirements, and business impact
3. Classification: Assign appropriate classification level(s)
4. Labeling: Apply classification labels where technically feasible
5. Protection: Implement appropriate security controls
6. Monitoring: Ongoing compliance monitoring and periodic review
7. Review: Classification reviewed annually or when significant changes occur

## 7. Exceptions and Waivers
- Legal holds or litigation requirements may temporarily override classification requirements
- Regulatory inspections or audits may require specific handling
- Business process changes may necessitate classification review
- Formal exception process: Written request to Information Security with business justification, risk assessment, and mitigation plan
- Exceptions time-limited and subject to review; never granted for Restricted or Special Categories without compensating controls

## 8. Revision History
- v1.0: Initial release (January 1, 2025)
- v2.0: Expanded classification levels, added Special Categories, formalized processes (September 1, 2025)