// Test hex literals
console.log(0xFF);
console.log(0b1010);
console.log(0o17);

// Test: Number(), String(), Boolean() as functions
console.log(Number("42"));
console.log(Number(true));
console.log(String(123));
console.log(Boolean(0));
console.log(Boolean("hello"));

// Test: Object.keys / entries / values
let obj = { a: 1, b: 2, c: 3 };
console.log(Object.keys(obj).join(", "));
console.log(Object.values(obj).join(", "));

// Test: Array destructuring
let [first, second, ...rest] = [10, 20, 30, 40, 50];
console.log(first);
console.log(second);
console.log(rest.join(", "));

// Test: Object destructuring
let { name, age } = { name: "Bob", age: 30 };
console.log(name + " " + age);

// Test: for...in
let person = { x: 1, y: 2, z: 3 };
let keys = [];
for (let k in person) { keys.push(k); }
console.log(keys.join(", "));

// Test: find / some / every
let nums = [1, 2, 3, 4, 5];
console.log(nums.find(x => x > 3));
console.log(nums.some(x => x > 4));
console.log(nums.every(x => x > 0));

// Test: JSON
let data = { score: 100, name: "Alice" };
let json = JSON.stringify(data);
console.log(typeof json);
let parsed = JSON.parse(json);
console.log(parsed.score);
