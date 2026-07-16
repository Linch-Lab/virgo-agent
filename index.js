const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files from current directory
app.use(express.static(__dirname));

// / → landing page (marketing)
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'landing.html'));
});

// /login → sign in page
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, 'login.html'));
});

// /app → main app (requires login)
app.get('/app', (req, res) => {
  res.sendFile(path.join(__dirname, 'virgo_mvp.html'));
});

// Also serve uploads explicitly
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

app.listen(PORT, () => {
  console.log(`Virgo Agent running on port ${PORT}`);
});
