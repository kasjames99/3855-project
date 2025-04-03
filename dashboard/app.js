const baseUrl = ''; // This will be your Nginx server address

// New URLs using the Nginx proxy paths
const PROCESSING_STATS_URL = `${baseUrl}/analyzer/stats`;
const ANALYZER_STATS_URL = `${baseUrl}/processing/stats`;
const currentTime = new Date().toISOString();
const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
const EVENT_TYPE_1_URL = `${baseUrl}/storage/events/motion?start_timestamp=${encodeURIComponent(thirtyDaysAgo)}&end_timestamp=${encodeURIComponent(currentTime)}`;
const EVENT_TYPE_2_URL = `${baseUrl}/storage/events/temperature?start_timestamp=${encodeURIComponent(thirtyDaysAgo)}&end_timestamp=${encodeURIComponent(currentTime)}`;

// DOM Elements
const processingStatsEl = document.getElementById('processing-stats');
const analyzerStatsEl = document.getElementById('analyzer-stats');
const eventType1El = document.getElementById('event-type-1');
const eventType2El = document.getElementById('event-type-2');
const lastUpdatedTimeEl = document.getElementById('last-updated-time');

// Helper function to create a table from JSON data
function createTableFromJSON(data) {
    if (!data || Object.keys(data).length === 0) {
        return '<p>No data available</p>';
    }

    let table = '<table><tr><th>Property</th><th>Value</th></tr>';
    
    for (const [key, value] of Object.entries(data)) {
        if (typeof value !== 'object') {
            table += `<tr><td>${key}</td><td>${value}</td></tr>`;
        } else {
            table += `<tr><td>${key}</td><td>${JSON.stringify(value)}</td></tr>`;
        }
    }
    
    table += '</table>';
    return table;
}

// Function to format the current date and time
function formatDateTime() {
    const now = new Date();
    return now.toLocaleString();
}

// Function to update the last updated time
function updateLastUpdatedTime() {
    lastUpdatedTimeEl.textContent = formatDateTime();
}

// Function to fetch data from an API endpoint
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching data from ${url}:`, error);
        return { error: `Failed to fetch data: ${error.message}` };
    }
}

// Function to update all dashboard data
async function updateDashboard() {
    try {
        // Fetch data from all endpoints
        const processingStats = await fetchData(PROCESSING_STATS_URL);
        const analyzerStats = await fetchData(ANALYZER_STATS_URL);
        
        // Fetch motion and temperature events
        const motionEvents = await fetchData(EVENT_TYPE_1_URL);
        const temperatureEvents = await fetchData(EVENT_TYPE_2_URL);
        
        // Get the most recent event from each array
        let mostRecentMotion = { message: "No motion events found" };
        if (Array.isArray(motionEvents) && motionEvents.length > 0) {
            mostRecentMotion = motionEvents[motionEvents.length - 1]; // Assuming the API returns events sorted by time
        }
        
        let mostRecentTemperature = { message: "No temperature events found" };
        if (Array.isArray(temperatureEvents) && temperatureEvents.length > 0) {
            mostRecentTemperature = temperatureEvents[temperatureEvents.length - 1];
        }
        
        // Update the DOM with fetched data
        processingStatsEl.innerHTML = createTableFromJSON(processingStats);
        analyzerStatsEl.innerHTML = createTableFromJSON(analyzerStats);
        eventType1El.innerHTML = createTableFromJSON(mostRecentMotion);
        eventType2El.innerHTML = createTableFromJSON(mostRecentTemperature);
        
        // Update the last updated time
        updateLastUpdatedTime();
    } catch (error) {
        console.error("Error updating dashboard:", error);
    }
}

// Initial update
updateDashboard();

// Set up periodic updates (every 3 seconds)
setInterval(updateDashboard, 3000);