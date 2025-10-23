# LumiX Documentation

This directory contains the Sphinx documentation for LumiX.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e .[docs]
```

Or if you're developing:

```bash
pip install -e .[dev,docs]
```

### Build HTML Documentation

From the `docs/` directory:

```bash
cd docs
make html
```

The built documentation will be in `docs/build/html/`. Open `docs/build/html/index.html` in your browser to view it.

### Other Formats

```bash
# PDF (requires LaTeX)
make latexpdf

# EPUB
make epub

# Plain text
make text
```

### Clean Build

To clean previous builds:

```bash
make clean
```

### Live Reload (Development)

For auto-rebuilding during development, you can use `sphinx-autobuild`:

```bash
pip install sphinx-autobuild
sphinx-autobuild source build/html
```

Then open http://127.0.0.1:8000 in your browser.

## Documentation Structure

```
docs/
├── source/
│   ├── index.rst                    # Main landing page
│   ├── getting-started/
│   │   ├── installation.rst         # Installation guide
│   │   ├── quickstart.rst          # Quick start tutorial
│   │   └── solvers.rst             # Solver overview and comparison
│   ├── user-guide/
│   │   └── index.rst               # User guide (placeholder)
│   ├── api/
│   │   └── index.rst               # API reference (placeholder)
│   ├── examples/
│   │   └── index.rst               # Examples overview (placeholder)
│   ├── _static/                    # Static files (CSS, JS, images)
│   └── _templates/                 # Custom Sphinx templates
├── build/                          # Generated documentation (gitignored)
├── Makefile                        # Build commands (Unix)
├── make.bat                        # Build commands (Windows)
└── README.md                       # This file
```

## Configuration

The Sphinx configuration is in `source/conf.py`. Key settings:

- **Theme**: Furo (modern, clean theme)
- **Extensions**:
  - `sphinx.ext.autodoc` - Auto-generate API docs from docstrings
  - `sphinx.ext.napoleon` - Support for Google/NumPy docstrings
  - `sphinxcontrib.mermaid` - Mermaid diagram support
  - `sphinx_autodoc_typehints` - Type hint support
  - `sphinx.ext.intersphinx` - Cross-reference other projects

## Contributing to Documentation

### Adding New Pages

1. Create a new `.rst` file in the appropriate directory
2. Add it to the relevant `toctree` directive
3. Build and preview locally
4. Submit a pull request

### Writing Style Guide

- Use **second person** ("you") when addressing readers
- Use **present tense** for descriptions
- Use **imperative mood** for instructions
- Include **code examples** where appropriate
- Add **cross-references** to related content

### reStructuredText Basics

```rst
Section Title
=============

Subsection
----------

**Bold text**
*Italic text*
``Code``

.. code-block:: python

   # Code block
   from lumix import LXModel

.. note::
   This is a note.

.. warning::
   This is a warning.

:doc:`Link to another page <getting-started/installation>`
```

## Current Status

### ✅ Completed

- Documentation infrastructure (Sphinx + Furo + Mermaid)
- Index page with overview
- Installation guide
- Quick start tutorial
- Comprehensive solver guide with comparison
- Placeholder pages for future content

### 🚧 In Progress

- User guide sections
- API reference documentation
- Example documentation

### 📋 Planned

- Advanced tutorials
- Best practices guide
- Troubleshooting guide
- Performance optimization guide
- Contributing guide
- Changelog

## Updating Documentation

After making changes:

1. **Build locally** to verify
2. **Check for warnings** in the build output
3. **Preview in browser** to ensure formatting is correct
4. **Commit and push** your changes

## Deployment

Documentation can be deployed to:

- **Read the Docs**: Automatic builds from GitHub
- **GitHub Pages**: Manual or automated deployment
- **Other hosting**: Export as static HTML

For Read the Docs, add a `.readthedocs.yaml` file in the repository root.

## Help

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Furo Theme Docs](https://pradyunsg.me/furo/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Mermaid Documentation](https://mermaid.js.org/)
