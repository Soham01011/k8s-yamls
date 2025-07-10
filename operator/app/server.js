const express = require('express');
const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Configuration
const MONGO_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/numbersDB';
const LOG_FILE = process.env.LOG_FILE || 'numbers.log';
const LOG_DIR = path.join(__dirname, 'logs');
const LOG_PATH = path.join(LOG_DIR, LOG_FILE);

// Ensure log directory exists
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

// Number schema and model
const numberSchema = new mongoose.Schema({
  value: {
    type: Number,
    required: true
  },
  timestamp: {
    type: Date,
    default: Date.now
  }
});

const NumberModel = mongoose.model('Number', numberSchema);

// Connect to MongoDB
async function connectDB() {
  try {
    await mongoose.connect(MONGO_URI);
    console.log('Connected to MongoDB');
  } catch (error) {
    console.error('MongoDB connection error:', error);
    process.exit(1);
  }
}

// Log number to file
function logToFile(number) {
  const logEntry = `${new Date().toISOString()} - ${number}\n`;
  fs.appendFile(LOG_PATH, logEntry, (err) => {
    if (err) {
      console.error('Error writing to log file:', err);
    }
  });
}

// Middleware
app.use(express.json());

// Ping endpoint
app.get('/ping', (req, res) => {
  res.json({ message: 'pong', timestamp: new Date().toISOString() });
});

// Random number endpoint
app.get('/random', async (req, res) => {
  const randomNumber = Math.floor(Math.random() * 1000); // 0-999
  
  try {
    // Save to MongoDB
    const newNumber = await NumberModel.create({ value: randomNumber });
    
    // Log to console
    console.log(`Generated random number: ${randomNumber}`);
    
    // Log to file
    logToFile(randomNumber);
    
    res.json({ 
      number: randomNumber,
      dbId: newNumber._id,
      timestamp: newNumber.timestamp,
      loggedToFile: true
    });
    
  } catch (error) {
    console.error('Error processing number:', error);
    res.status(500).json({ error: 'Failed to process number' });
  }
});

// Start server
connectDB().then(() => {
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Logging numbers to: ${LOG_PATH}`);
  });
});

// Handle shutdown
process.on('SIGINT', async () => {
  await mongoose.disconnect();
  console.log('Disconnected from MongoDB');
  process.exit(0);
});
