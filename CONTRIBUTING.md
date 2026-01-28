# Contributing to bigstat42

Thank you for your interest in contributing to bigstat42! This document provides guidelines for contributing to the project.

## Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/bigstat42.git
cd bigstat42
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

3. Test your setup:
```bash
python demo.py
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable names

## Testing

Before submitting changes:

1. Run the demo to verify basic functionality:
```bash
python demo.py
```

2. Test the main application help:
```bash
python run.py --help
bigstat42 --help
```

3. Verify syntax:
```bash
python -m py_compile bigstat42/*.py
```

## Pull Request Process

1. Create a new branch for your feature:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and commit:
```bash
git add .
git commit -m "Description of your changes"
```

3. Push to your fork:
```bash
git push origin feature/your-feature-name
```

4. Open a Pull Request on GitHub with:
   - Clear description of changes
   - Reason for the changes
   - Any breaking changes noted

## Potential Areas for Contribution

### Features
- Add more visualization types (line charts, pie charts)
- Export data to CSV/JSON formats
- Add filtering options (by user, by host pattern)
- Create a web dashboard interface
- Add caching for API responses
- Support for multiple campuses in one run

### Improvements
- Better error handling and retry logic for API calls
- Progress bars for long-running operations
- Configuration file support (YAML/JSON)
- Unit tests and integration tests
- Performance optimizations for large datasets
- Docker support

### Documentation
- More examples in README
- Video tutorials
- Translation to other languages
- API endpoint documentation

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about the codebase
- Suggestions for improvements

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
