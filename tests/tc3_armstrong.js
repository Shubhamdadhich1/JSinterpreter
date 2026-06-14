function isArmstrong(n) {
    let digits = String(n).split("");
    let len = digits.length;
    let sum = 0;
    for (let d of digits) {
        sum += Math.pow(parseInt(d), len);
    }
    return sum === n;
}

console.log(isArmstrong(153));
console.log(isArmstrong(123));
