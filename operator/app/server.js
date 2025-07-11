const express = require('express');
const mongoose = require('mongoose');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Enhanced Configuration
const MONGO_URI = process.env.MONGO_URI || 'mongodb://mongodb:27017/numbersDB'; // Changed to service name
const LOG_FILE = process.env.LOG_FILE || 'numbers.log';
const LOG_DIR = '/data/logs';  // Changed to PVC-mounted path
const LOG_PATH = path.join(LOG_DIR, LOG_FILE);

// write to file
function logToFile(number) {
  const logEntry = `${new Date().toISOString()} - ${number}\n`;

  fs.appendFile(LOG_PATH, logEntry, (err) => {
    if (err) {
      console.error(`Failed to write to log file at ${LOG_PATH}:`, err);
    } else {
      console.log(`Logged number ${number} to ${LOG_PATH}`);
    }
  });
}

// Create log directory if needed
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

// Number schema and model
const numberSchema = new mongoose.Schema({
  value: { type: Number, required: true },
  timestamp: { type: Date, default: Date.now }
});
const NumberModel = mongoose.model('Number', numberSchema);

// Enhanced MongoDB connection with retries
async function connectDB() {
  const maxRetries = 5;
  let retryCount = 0;
  
  while (retryCount < maxRetries) {
    try {
      await mongoose.connect(MONGO_URI, {
        serverSelectionTimeoutMS: 5000,
        socketTimeoutMS: 45000
      });
      console.log('Connected to MongoDB');
      return;
    } catch (error) {
      retryCount++;
      console.error(`MongoDB connection attempt ${retryCount} failed:`, error.message);
      if (retryCount === maxRetries) {
        console.error('Max retries reached. Exiting...');
        process.exit(1);
      }
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
}

// Start server independently of MongoDB
async function startServer() {
  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Logging numbers to: ${LOG_PATH}`);
  });

  // Enhanced error handling
  server.on('error', (error) => {
    console.error('Server error:', error);
    process.exit(1);
  });
}

// Middleware
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'UP',
    db: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected',
    timestamp: new Date().toISOString()
  });
});

// Random number endpoint
app.get('/random', async (req, res) => {
  if (mongoose.connection.readyState !== 1) {
    return res.status(503).json({ error: 'Database not connected' });
  }

  const randomNumber = Math.floor(Math.random() * 1000);
  
  try {
    const newNumber = await NumberModel.create({ value: randomNumber });
    logToFile(randomNumber);
    res.json({ 
      number: randomNumber,
      dbId: newNumber._id,
      timestamp: newDate().toISOString()
    });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: 'Processing failed' });
  }
});

// Start everything
(async () => {
  try {
    await connectDB();
    await startServer();
  } catch (error) {
    console.error('Fatal startup error:', error);
    process.exit(1);
  }
})();

// Handle shutdown
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

async function gracefulShutdown() {
  console.log('Shutting down gracefully...');
  await mongoose.disconnect();
  process.exit(0);
}
