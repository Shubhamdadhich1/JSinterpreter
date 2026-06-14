# ⚡ JSRunner — JavaScript Interpreter in Pure Python

> **Thunder Hackathon 2.0** — A fully working JavaScript runtime written in pure Python 3.
> No Node.js. No external libraries. Zero dependencies. Just Python.


---

## 🚀 How to Run

### Requirements
- Python 3.x (that's it — nothing else to install)

### Run a test case
```bash
python jsrunner.py tests/tc1_odd_even.txt
python jsrunner.py tests/tc2_triangle.js
python jsrunner.py tests/tc3_armstrong.js
python jsrunner.py tests/tc4_array_reverse.js
python jsrunner.py tests/tc5_palindrome.js
```

### Run your own JS file
```bash
python jsrunner.py yourfile.js
```

### Run inline code
```bash
echo "console.log('Hello, World!')" | python jsrunner.py -
```

---

## ✅ All 5 Test Cases — Verified Output

### TC1 — Odd / Even Checker
```bash
python jsrunner.py tests/tc1_odd_even.txt
```
```
7 is Odd
```

### TC2 — Triangle Pattern
```bash
python jsrunner.py tests/tc2_triangle.js
```
```
*
**
***
****
*****
```

### TC3 — Armstrong Number
```bash
python jsrunner.py tests/tc3_armstrong.js
```
```
true
false
```

### TC4 — Array Reverse
```bash
python jsrunner.py tests/tc4_array_reverse.js
```
```
Original: 1, 2, 3, 4, 5
Reversed: 5, 4, 3, 2, 1
```

### TC5 — String Palindrome
```bash
python jsrunner.py tests/tc5_palindrome.js
```
```
racecar is a Palindrome
```

---

## 📁 Project Structure

```
JSinterpreter/
├── jsrunner.py          ← The entire interpreter (single file, ~2700 lines)
├── README.md
└── tests/
    ├── tc1_odd_even.txt
    ├── tc2_triangle.js
    ├── tc3_armstrong.js
    ├── tc4_array_reverse.js
    ├── tc5_palindrome.js
    └── extra_test.js
```

---

## 🏗️ How It Works

The interpreter is a classic three-stage pipeline, built entirely from scratch:

```
JS Source Code
      │
      ▼
┌──────────┐
│  LEXER   │  Characters → Token stream
└────┬─────┘  Handles strings, template literals, hex/octal/binary
     │
     ▼
┌──────────┐
│  PARSER  │  Tokens → AST (recursive descent)
└────┬─────┘  Full JS operator precedence
     │
     ▼
┌─────────────┐
│  EVALUATOR  │  AST → Output (tree-walking interpreter)
└──────┬──────┘  Lexical scoping, closures, prototype chain
       │
       ▼
   stdout
```

---

## ✨ Supported JavaScript Features

| Feature | Supported |
|---|---|
| `let`, `const`, `var`, hoisting | ✅ |
| `if / else if / else`, `switch` | ✅ |
| `for`, `while`, `do...while`, `for...of`, `for...in` | ✅ |
| Functions, arrow functions, closures | ✅ |
| Classes, `new`, `this`, `extends` | ✅ |
| Array & object destructuring | ✅ |
| Spread `...` and rest `...` operators | ✅ |
| Template literals with `${}` | ✅ |
| `try / catch / finally`, `throw` | ✅ |
| All Array methods (`map`, `filter`, `reduce`, `find`, etc.) | ✅ |
| All String methods (`split`, `replace`, `trim`, etc.) | ✅ |
| `Math`, `Date`, `JSON`, `parseInt`, `parseFloat` | ✅ |
| Type coercion, `typeof`, `instanceof` | ✅ |
| Hex `0xFF`, octal `0o17`, binary `0b1010` literals | ✅ |
| `console.log`, `console.error`, `console.warn` | ✅ |

---

## 🔑 Key Design Choices

| Choice | Why |
|---|---|
| Single Python file | Zero setup — just `python jsrunner.py file.js` |
| AST nodes as plain `dict` | No class overhead, fast tree construction |
| All JS numbers as Python `float` | Matches JS IEEE-754 double precision exactly |
| Signals via Python exceptions | Clean control flow for `return` / `break` / `continue` / `throw` |
| `Env` chain for scoping | Correct closures, block scope for `let`/`const`, hoisting for `var` |

---

Built for ⚡ Thunder Hackathon 2.0 · Pure Python 3 · Zero dependencies