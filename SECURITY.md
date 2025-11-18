# Security Policy

## Supported Versions

We release security updates for the following versions:

| Project | Version | Supported          |
| ------- | ------- | ------------------ |
| Package Manager TUI | latest (main) | :white_check_mark: |
| Update Catalog Fetcher | latest (main) | :white_check_mark: |
| Earlier commits | - | :x:                |

**Note**: This repository contains multiple Python projects. Security fixes are applied to the main branch only.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in any Python utilities in this repository, please report it responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by:

1. **Using GitHub Security Advisories** (preferred)
   - Go to the [Security tab](https://github.com/jesse-slaton/python/security/advisories)
   - Click "Report a vulnerability"
   - Fill out the form with details

2. **Email** (alternative)
   - Send an email to the repository maintainer
   - Include "SECURITY - Python Utilities" in the subject line
   - Provide detailed information about the vulnerability

### What to Include

When reporting a vulnerability, please include:

- **Project Name**: Which tool is affected (Package Manager TUI, Update Catalog Fetcher, etc.)
- **Description**: A clear description of the vulnerability
- **Impact**: What an attacker could do with this vulnerability
- **Attack Scenario**: How the vulnerability could be exploited
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Affected Versions**: Which versions are affected
- **Suggested Fix**: If you have ideas for a fix (optional)
- **Proof of Concept**: Code that demonstrates the issue (if applicable)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
- **Updates**: We will provide regular updates on our progress (at least every 7 days)
- **Timeline**: We aim to release a fix within 90 days for critical vulnerabilities
- **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

### Safe Harbor

We support safe harbor for security researchers who:

- Make a good faith effort to avoid privacy violations, data destruction, and service interruption
- Only test against your own systems or with explicit permission
- Do not exploit the vulnerability beyond the minimum necessary to demonstrate the issue
- Report vulnerabilities promptly
- Keep the vulnerability confidential until it has been resolved

We will not pursue legal action against researchers who follow these guidelines.

## Security Considerations

### Package Manager TUI

The package manager TUI interacts with system package managers and can install/remove software:

#### Key Security Concerns

1. **Package Installation**
   - Installs packages from configured sources (winget, etc.)
   - Requires elevated privileges for system-wide installations
   - **Risk**: Malicious package installation, privilege escalation

2. **Command Execution**
   - Executes package manager commands
   - Processes command output
   - **Risk**: Command injection, arbitrary code execution

3. **Network Operations**
   - Fetches package metadata and binaries
   - Communicates with package repositories
   - **Risk**: Man-in-the-middle attacks, compromised repositories

4. **Input Handling**
   - Processes package names and search queries
   - Handles user selections
   - **Risk**: Injection attacks, denial of service

### Update Catalog Fetcher

This tool downloads Windows updates and generates deployment packages:

#### Key Security Concerns

1. **Update Downloads**
   - Downloads update files from Microsoft Update Catalog
   - Validates update metadata
   - **Risk**: Malicious update injection, file tampering

2. **Script Generation**
   - Generates PowerShell installation scripts
   - Creates Tanium Deploy package metadata
   - **Risk**: Script injection, malicious code generation

3. **File System Operations**
   - Creates directories and files
   - Writes executable content
   - **Risk**: Path traversal, arbitrary file write

4. **Web Scraping**
   - Parses HTML from Microsoft Update Catalog
   - Processes user-provided KB numbers
   - **Risk**: SSRF, XSS in parsing, denial of service

### General Python Security Concerns

1. **Dependency Vulnerabilities**
   - Third-party packages may have vulnerabilities
   - Keep dependencies updated
   - Monitor security advisories

2. **Arbitrary Code Execution**
   - Be cautious with `eval()`, `exec()`, `__import__()`
   - Validate and sanitize all inputs
   - Use subprocess safely

3. **Path Traversal**
   - Validate file paths from user input
   - Use `os.path.normpath()` and validate against allowed directories
   - Avoid `..` in paths

4. **Credential Handling**
   - Never hardcode credentials
   - Use environment variables or secure vaults
   - Avoid logging sensitive data

## Known Security Limitations

- **Work in Progress**: Projects are under active development
- **Limited Input Validation**: Some user inputs may not be fully validated
- **No Code Signing**: Scripts and packages are not currently signed
- **Dependency Scanning**: Automated dependency vulnerability scanning not yet implemented

## Security Best Practices

When using Python utilities from this repository:

1. **Verify Before Execution**
   - Review source code before running
   - Understand what the tool does
   - Check for recent security issues

2. **Virtual Environments**
   - Use Python virtual environments (`venv`)
   - Isolate dependencies per project
   - Avoid global package installations

3. **Dependency Management**
   - Regularly update dependencies: `pip install --upgrade -r requirements.txt`
   - Use `pip-audit` to check for known vulnerabilities
   - Review dependency changes in updates

4. **Least Privilege**
   - Run tools with minimum necessary permissions
   - Use non-admin accounts when possible
   - Request elevation only when required

5. **Input Validation**
   - Be cautious with user-provided KB numbers, package names, etc.
   - Validate inputs match expected formats
   - Sanitize inputs before passing to external commands

6. **Network Security**
   - Use HTTPS for all network communications
   - Validate SSL/TLS certificates
   - Be cautious with proxy configurations

7. **File System Security**
   - Verify download integrity (checksums, signatures)
   - Use secure temporary directories
   - Clean up temporary files after use

8. **Logging**
   - Enable logging for audit trails
   - Avoid logging credentials or sensitive data
   - Secure log file permissions

## Common Vulnerability Types

Be especially cautious of:

- **Command Injection**: Unsanitized input passed to `subprocess`, `os.system()`, etc.
- **Path Traversal**: File operations with user-controlled paths
- **Dependency Vulnerabilities**: Outdated or vulnerable third-party packages
- **SSRF**: HTTP requests with user-controlled URLs
- **Deserialization**: Unsafe unpickling or YAML loading
- **Code Injection**: Using `eval()` or `exec()` with untrusted input
- **XXE**: XML parsing vulnerabilities
- **Credential Exposure**: Credentials in logs, error messages, or version control

## Secure Development Guidelines

When contributing to these projects:

1. **Input Validation**
   ```python
   # Good: Validate and sanitize
   if not re.match(r'^KB\d{7}$', kb_number):
       raise ValueError("Invalid KB number format")

   # Bad: Trust user input
   subprocess.run(f"winget install {package_name}", shell=True)
   ```

2. **Subprocess Safety**
   ```python
   # Good: Use list form, no shell
   subprocess.run(["winget", "install", package_name], check=True)

   # Bad: Shell=True with user input
   subprocess.run(f"winget install {package_name}", shell=True)
   ```

3. **Path Handling**
   ```python
   # Good: Validate paths
   base_dir = Path("/safe/directory")
   user_path = (base_dir / user_input).resolve()
   if not user_path.is_relative_to(base_dir):
       raise ValueError("Path traversal detected")

   # Bad: Trust user paths
   with open(user_input, 'w') as f:
       f.write(data)
   ```

4. **Secrets Management**
   ```python
   # Good: Use environment variables
   api_key = os.getenv("API_KEY")

   # Bad: Hardcode secrets
   api_key = "sk_live_abc123..."
   ```

## Disclosure Policy

- We follow a **coordinated disclosure** policy
- Security issues will be disclosed publicly after a fix is available
- We will publish a security advisory with details of the vulnerability and the fix
- Critical vulnerabilities will be fast-tracked for release

## Contributing Security Fixes

If you'd like to contribute a security fix:

1. Report the vulnerability first (as described above)
2. Wait for acknowledgment before submitting a PR
3. Submit the PR to a private branch if requested
4. Include security impact assessment in PR description
5. Follow the coding standards in `DEVELOPMENT.md`
6. Add tests that verify the fix

## Contact

For security-related questions that are not vulnerabilities, you can:

- Open a regular GitHub issue with the `security` label
- Use the Discussions tab for general security questions

Thank you for helping keep our tools and users safe!
