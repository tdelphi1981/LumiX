# Security Policy

## Supported Versions

We take security seriously and aim to address vulnerabilities promptly. The following versions of LumiX are currently supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

As LumiX is currently in early development (v0.1.1), we recommend always using the latest version available.

## Reporting a Vulnerability

If you discover a security vulnerability in LumiX, please help us by reporting it responsibly. We appreciate your efforts to disclose your findings in a coordinated manner.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by email to:

- **Tolga BERBER**: tolga.berber@fen.ktu.edu.tr
- **Beyzanur SİYAH**: beyzanursiyah@ktu.edu.tr

Please include the following information in your report:

1. **Description**: A clear description of the vulnerability
2. **Impact**: Potential impact and severity of the issue
3. **Reproduction**: Step-by-step instructions to reproduce the vulnerability
4. **Version**: LumiX version(s) affected
5. **Environment**: Python version, operating system, and solver backends used
6. **Proof of Concept**: Code snippet or example demonstrating the issue (if applicable)
7. **Suggested Fix**: Any ideas for how to fix the vulnerability (optional)

### What to Expect

When you report a security issue, you can expect:

1. **Acknowledgment**: We will acknowledge receipt of your report within 72 hours
2. **Assessment**: We will assess the vulnerability and determine its severity
3. **Updates**: We will keep you informed of our progress
4. **Timeline**: We aim to release a fix within 30 days for critical vulnerabilities
5. **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

### Disclosure Policy

- We follow a **coordinated disclosure** process
- We request that you do not publicly disclose the vulnerability until we have released a fix
- Once a fix is released, we will publish a security advisory
- We will credit security researchers who report vulnerabilities (with permission)

## Security Considerations

### Solver Security

LumiX interfaces with multiple optimization solvers (OR-Tools, Gurobi, CPLEX, GLPK). Please note:

- **Solver Dependencies**: Each solver has its own security considerations and licensing
- **Untrusted Input**: Be cautious when building models from untrusted user input
- **Resource Limits**: Set appropriate time limits and resource constraints for solver execution
- **Solver Logs**: Be aware that solvers may write log files to disk

### Code Execution

When using LumiX:

- **Model Construction**: Models built from untrusted data should be validated
- **Expression Evaluation**: Be careful with dynamically generated constraints
- **File Operations**: LumiX reads/writes solver files; ensure proper file permissions
- **Data Validation**: Validate input data before passing to optimization models

### Dependencies

LumiX depends on several third-party packages. We:

- Monitor dependencies for known vulnerabilities
- Update dependencies when security patches are released
- Use only well-maintained packages from trusted sources

To check for known vulnerabilities in dependencies:

```bash
pip install pip-audit
pip-audit
```

## Security Best Practices

When using LumiX in production:

1. **Keep Updated**: Always use the latest version of LumiX
2. **Input Validation**: Validate all user inputs before model construction
3. **Resource Limits**: Set solver time limits and memory constraints
4. **Least Privilege**: Run solver processes with minimal required permissions
5. **Environment Isolation**: Use virtual environments to isolate dependencies
6. **Audit Logs**: Monitor solver logs for unusual activity
7. **License Compliance**: Ensure proper licensing for commercial solvers

## Known Security Limitations

As an early-stage project (v0.1.1):

- **Alpha Stage**: The API is not yet stable and may contain undiscovered vulnerabilities
- **Limited Testing**: Security testing is ongoing but not comprehensive
- **Solver Interfaces**: Security depends partly on the underlying solver implementations
- **Academic Focus**: Primary focus is on research use cases, not hardened production environments

## Commercial Solver Considerations

When using commercial solvers (Gurobi, CPLEX):

- **License Files**: Protect license files and credentials
- **Network Licenses**: Secure communication with license servers
- **Audit Trails**: Commercial solvers may maintain usage logs
- **Support**: Contact your solver vendor for solver-specific security issues

## Academic Research Context

LumiX is primarily designed for academic research. If you are using LumiX in security-sensitive applications:

- Perform additional security review and testing
- Consider the alpha stage of the project
- Implement appropriate safeguards for your use case
- Contact us to discuss your security requirements

## Security Updates

Security updates will be:

- Released as patch versions (e.g., 0.1.2 for a security fix to 0.1.1)
- Announced in the CHANGELOG with a [SECURITY] tag
- Published as GitHub Security Advisories
- Communicated to users via GitHub releases

## Contact

For security-related questions or concerns:

- **Email**: tolga.berber@fen.ktu.edu.tr, beyzanursiyah@ktu.edu.tr
- **General Questions**: Use GitHub Discussions for non-sensitive questions

## Acknowledgments

We thank the security research community for their efforts in keeping open-source software secure. Responsible disclosure helps protect all users of LumiX.

---

**Last Updated**: January 2025
