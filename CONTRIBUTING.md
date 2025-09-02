# Contributing to Xian Universal Wallet Protocol

Thank you for your interest in contributing to the Xian Universal Wallet Protocol! This document provides guidelines for contributing to the project.

## How to Contribute

### 1. Protocol Improvements

To propose changes to the protocol specification:

1. Open an issue describing the proposed change
2. Discuss with the community
3. Submit a Pull Request with:
   - Updated `protocol/SPECIFICATION.md`
   - Updated `protocol/openapi.yaml`
   - New test vectors if applicable
   - Rationale for the change

### 2. New Language Implementation

To contribute a new language implementation:

1. Implement the protocol following the specification
2. Ensure compliance using the test vectors
3. Create a directory: `implementations/[language]/`
4. Include:
   - Source code
   - README with usage instructions
   - Compliance report
   - Example usage

### 3. Bug Reports

When reporting bugs:

1. Check existing issues first
2. Provide:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages/logs

### 4. Documentation

Documentation improvements are always welcome:

- Fix typos or clarify existing docs
- Add examples
- Improve guides
- Translate documentation

## Development Process

### 1. Fork and Clone

```bash
git clone https://github.com/[your-username]/xian-uwp
cd xian-uwp
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow existing code style
- Add tests for new features
- Update documentation
- Ensure all tests pass

### 3. Test Your Changes

```bash
# For Python reference implementation
cd reference/python
pip install -e ".[dev]"
pytest

# Run compliance tests
python protocol/validator.py --url http://localhost:8545
```

### 4. Submit Pull Request

- Clear title and description
- Reference any related issues
- Ensure CI passes
- Be responsive to feedback

## Code Standards

### Python (Reference Implementation)

- Follow PEP 8
- Use type hints
- Add docstrings
- Format with `black`
- Lint with `flake8`

### Protocol Specification

- Use clear, unambiguous language
- Follow RFC 2119 for requirement levels
- Include examples
- Consider extensibility for future features

### Test Vectors

- Cover both success and failure cases
- Use descriptive IDs and descriptions
- Follow existing format
- Test edge cases

## Commit Messages

Follow conventional commits:

```
feat: add new endpoint for token metadata
fix: correct session expiry calculation
docs: update implementation guide
test: add test vectors for error cases
refactor: simplify authorization flow
```

## Review Process

1. **Automated checks**: CI must pass
2. **Code review**: At least one maintainer approval
3. **Testing**: Compliance tests must pass
4. **Documentation**: Must be updated if needed

## Community

- **Discord**: [Join our Discord](https://discord.gg/xian)
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Use GitHub Issues for bugs/features

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Given credit in documentation

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards

**Positive behaviors:**
- Using welcoming language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what's best for the community

**Unacceptable behaviors:**
- Harassment of any kind
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

### Enforcement

Project maintainers will enforce these standards. Violations may result in temporary or permanent bans.

## Questions?

If you have questions about contributing:

1. Check the [documentation](docs/)
2. Ask in [GitHub Discussions](https://github.com/xian-network/xian-uwp/discussions)
3. Join our [Discord](https://discord.gg/xian)

Thank you for contributing to the Xian Universal Wallet Protocol! 🚀