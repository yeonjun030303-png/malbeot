require('dotenv').config();
const admin = require('firebase-admin');
const serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  databaseURL: process.env.FIREBASE_DB_URL
});
admin.database().ref('/').once('value')
  .then(snap => console.log('연결 성공:', snap.exists()))
  .catch(err => console.error('연결 실패:', err.message));