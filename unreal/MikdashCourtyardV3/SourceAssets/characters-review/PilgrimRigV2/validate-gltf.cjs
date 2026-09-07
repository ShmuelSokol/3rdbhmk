const fs = require('fs');
const path = require('path');
const validator = require('./validation-tools');
const file = path.join(__dirname, 'PilgrimRigV2.glb');
validator.validateBytes(new Uint8Array(fs.readFileSync(file)), {
  uri: 'PilgrimRigV2.glb', maxIssues: 1000,
}).then(report => {
  fs.writeFileSync(path.join(__dirname, 'khronos-validation.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report.issues));
  if (report.issues.numErrors) process.exitCode = 1;
}).catch(error => { console.error(error); process.exitCode = 1; });
