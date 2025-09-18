A few key rules to follow:

Work process
* First generate a .gitignore file to exclude the following: .env, .venv, .streamlit/secrets.toml, *.json, and all Pyc and similar files.
* Keep a README.md file and keep it updated as we build the code.
* Keep the test code updated as we update the main code, with a single-click run.

Code structure
* Wherever possible, follow the design of the corresponding code as in the sample_code folder, if one is available.
* Define a core_utils.py file with all the core utilities.
* Put the core python code in src directory and the test code in test directory. However, main app and requirements.txt should be in the home directory.
* Create a separate doc directory for user-facing documentation.

Code style
* Keep code compact. All methods should be no more than 30 lines of code. Each file should be less than 300 lines of code. Avoid complicated branches and logic.
* Generate the simplest, easy-to-read code. The code needs to be correct, but exercise good judgement in handling different cases and exception handling. 
* After testing code, ask if you should refactor the code to make it simpler for humans to understand.


