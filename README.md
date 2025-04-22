

## Testing a calculation service

1. Create a new python virtual environment
2. Install dependencies `pip install -r requirements.txt`
3. Install package `pip install -e .`
4. Run `cd test`
5. Run `python -m unittest discover -s ./ -p 'Test*.py'`
