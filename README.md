```javascript
module.exports = class Developer {
    constructor(name, role, age, [tech]) {
        this.name = name
        this.role = role
        this.age = age
        this.tech = tech
    }
}


const Developer = require("./Developer");

const Gabriel = new Developer("Gabriel", "Software Engineer", 17, ["NodeJS", "MongoDB", "MySQL", "React", "Electron", "Typescript"])
```
