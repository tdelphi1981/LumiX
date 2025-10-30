Installation
============

LumiX requires Python 3.10 or higher.

Basic Installation
------------------

Install LumiX using pip:

.. code-block:: bash

   pip install lumix

This installs the core library with minimal dependencies. You'll need to install at least one solver separately.

Installing with Solvers
-----------------------

LumiX supports multiple optimization solvers. You can install them individually or all at once.

Individual Solvers
~~~~~~~~~~~~~~~~~~

**OR-Tools** (Free, Apache 2.0 License)

.. code-block:: bash

   pip install lumix[ortools]

**Gurobi** (Commercial/Academic License Required)

.. code-block:: bash

   pip install lumix[gurobi]

.. note::
   Gurobi requires a valid license. Academic licenses are available for free at https://www.gurobi.com/academia/

**CPLEX** (Commercial/Academic License Required)

.. code-block:: bash

   pip install lumix[cplex]

.. note::
   CPLEX requires a valid license. Academic licenses are available through IBM Academic Initiative.

**GLPK** (Free, GPL License)

.. code-block:: bash

   pip install lumix[glpk]

All Solvers
~~~~~~~~~~~

To install all supported solvers at once:

.. code-block:: bash

   pip install lumix[all-solvers]

.. warning::
   Commercial solvers (Gurobi, CPLEX) still require valid licenses even if installed.

Development Installation
------------------------

For development work on LumiX itself:

.. code-block:: bash

   git clone https://github.com/tdelphi1981/LumiX.git
   cd LumiX
   pip install -e .[dev]

This installs LumiX in editable mode with development dependencies including:

- pytest for testing
- mypy for type checking
- black for code formatting
- ruff for linting
- sphinx for documentation

Requirements
------------

**Python Version**

- Python >= 3.10

**Core Dependencies**

- typing-extensions >= 4.5.0
- numpy >= 1.24.0

**Optional Solver Dependencies**

- ortools >= 9.8.0
- gurobipy >= 11.0.0
- cplex >= 22.1.0
- swiglpk >= 5.0.0

Verifying Installation
----------------------

Verify your installation by checking the version:

.. code-block:: python

   import lumix
   print(lumix.__version__)

Check which solvers are available:

.. code-block:: python

   from lumix import LXOptimizer

   optimizer = LXOptimizer()

   # Try to use a solver
   try:
       optimizer.use_solver("ortools")
       print("OR-Tools is available")
   except ImportError:
       print("OR-Tools is not installed")

Common Issues
-------------

**Import Error: No module named 'ortools'**

Solution: Install the solver package:

.. code-block:: bash

   pip install ortools

**Gurobi License Error**

Solution: Ensure you have a valid Gurobi license installed. For academic licenses:

1. Register at https://www.gurobi.com/academia/
2. Download and install the license file as per Gurobi's instructions

**CPLEX Not Found**

Solution: Ensure CPLEX is properly installed and the Python API is accessible. For academic licenses:

1. Register for IBM Academic Initiative
2. Download and install CPLEX
3. Install the Python API from the CPLEX installation directory

Platform-Specific Notes
-----------------------

macOS
~~~~~

On macOS with Apple Silicon (M1/M2), some solvers may require Rosetta 2 or have specific installation procedures. Consult each solver's documentation.

.. code-block:: bash

   # For native ARM support with OR-Tools
   pip install ortools

Linux
~~~~~

Most solvers work out-of-the-box on Linux. Ensure you have the necessary system libraries:

.. code-block:: bash

   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install build-essential

Windows
~~~~~~~

On Windows, ensure you have Visual C++ redistributables installed for compiled packages.

Next Steps
----------

After installation, continue to:

- :doc:`quickstart` - Build your first optimization model
- :doc:`solvers` - Learn about available solvers and their capabilities
