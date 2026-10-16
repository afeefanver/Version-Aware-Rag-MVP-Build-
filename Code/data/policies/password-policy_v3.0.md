# Password Policy v3.0
**Effective Date:** January 1, 2026
**Supersedes:** v2.0
**Superseded By:** None (current)

## 1. Purpose
To establish standards for creating strong passwords to protect company systems and data from unauthorized access, aligning with NIST SP 800-63B and ISO 27001 requirements.

## 2. Scope
This policy applies to all employees, contractors, third-party users, and service accounts with access to company systems.

## 3. Policy Requirements

### 3.1 Password Complexity
- Minimum length: 12 characters (increased from 10)
- Must contain at least one uppercase letter
- Must contain at least one lowercase letter
- Must contain at least one digit
- Must contain at least two special characters from set: !@#$%^&*()-_=+[]{}|;:,.<>?
- No dictionary words or common sequences (e.g., "password123", "qwerty")
- No context-specific words (company name, username, etc.)

### 3.2 Password Age
- Maximum password age: 60 days (maintained from v2.0)
- Passwords must be changed every 60 days
- Password history: Remember last 24 passwords (increased from 10)
- Password reuse prohibited within 2 years

### 3.3 Account Lockout
- Maximum failed login attempts: 3 (maintained from v2.0)
- Account lockout duration: 60 minutes (increased from 45)
- Automatic unlock after lockout period
- After 3 lockouts in 24 hours, account requires IT unlock and manager approval
- After 5 lockouts in 7 days, mandatory security training required

### 3.4 Password Usage
- Passwords must not be shared with anyone under any circumstances
- Passwords must not be written down or stored in plain text
- Use of company-approved password managers is required for all accounts
- Passwords must not be reused across different systems
- Passwords must not be used as answers to security questions

### 3.5 Multi-Factor Authentication
- MFA is required for all access (local, remote, and administrative)
- MFA methods must include at least two factors from: something you know (password), something you have (token/app), something you are (biometric)
- MFA cannot be disabled for any account
- Backup MFA methods must be configured and tested quarterly

### 3.6 Additional Requirements
- Passwords must be changed immediately if compromise is suspected
- All passwords must be changed upon employee termination or role change
- Service account passwords must be rotated every 90 days
- Passwords transmitted over networks must use encrypted channels (TLS 1.2+)
- Password storage must use approved hashing algorithms (bcrypt, Argon2) with salt

## 4. Exceptions
- Emergency access accounts require dual-control and weekly rotation
- Legacy systems unable to meet these requirements must be documented and isolated
- Exceptions require CISO approval and quarterly review

## 5. Enforcement
Violations of this policy may result in disciplinary action up to and including termination.
Automated compliance checking is performed weekly, with violations reported to management.

## 6. Revision History
- v1.0: Initial release (January 1, 2025)
- v2.0: Updated complexity and lockout requirements (July 1, 2025)
- v3.0: NIST alignment, increased complexity, enhanced MFA requirements (January 1, 2026)