const baseUrl = window.location.hostname === 'localhost' ?
        'http://localhost:8000' :
        `http://${window.location.hostname}:8000`;

// New URLs using the Nginx proxy paths
const PROCESSING_STATS_URL = `${baseUrl}/analyzer/stats`;
const ANALYZER_STATS_URL = `${baseUrl}/processing/stats`;
const CONSISTENCY_CHECK_URL = `${baseUrl}/consistency_check/checks`;
const CONSISTENCY_UPDATE_URL = `${baseUrl}/consistency_check/update`;
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
const runConsistencyCheckBtn = document.getElementById('run-consistency-check');
const consistencyStatusEl = document.getElementById('consistency-status');
const consistencyResultsEl = document.getElementById('consistency-results');

// Counts table cells
const dbTempCountEl = document.getElementById('db-temp-count');
const dbMotionCountEl = document.getElementById('db-motion-count');
const queueTempCountEl = document.getElementById('queue-temp-count');
const queueMotionCountEl = document.getElementById('queue-motion-count');
const procTempCountEl = document.getElementById('proc-temp-count');
const procMotionCountEl = document.getElementById('proc-motion-count');

// Missing events info
const missingDbCountEl = document.getElementById('missing-db-count');
const missingQueueCountEl = document.getElementById('missing-queue-count');
const missingDbListEl = document.getElementById('missing-db-list');
const missingQueueListEl = document.getElementById('missing-queue-list');

// Tab buttons
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

// Add event listeners for tabs
tabButtons.forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons and contents
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Add active class to clicked button
        button.classList.add('active');
        
        // Show the corresponding tab content
        const tabId = button.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

// Function to run a new consistency check
async function runConsistencyCheck() {
    try {
        runConsistencyCheckBtn.disabled = true;
        consistencyStatusEl.innerHTML = '<p>Running consistency check...</p>';
        
        const response = await fetch(CONSISTENCY_UPDATE_URL, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const result = await response.json();
        
        consistencyStatusEl.innerHTML = `<p>Consistency check completed in ${result.processing_time_ms}ms</p>`;
        
        // Fetch and display the results
        await fetchConsistencyCheckResults();
        
    } catch (error) {
        console.error('Error running consistency check:', error);
        consistencyStatusEl.innerHTML = `<p>Error running consistency check: ${error.message}</p>`;
    } finally {
        runConsistencyCheckBtn.disabled = false;
    }
}

// Function to fetch consistency check results
async function fetchConsistencyCheckResults() {
    try {
        const response = await fetch(CONSISTENCY_CHECK_URL);
        
        if (response.status === 404) {
            // No results yet
            consistencyResultsEl.style.display = 'none';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const results = await response.json();
        
        // Display results
        consistencyResultsEl.style.display = 'block';
        
        // Update counts
        dbTempCountEl.textContent = results.counts.db.temperature;
        dbMotionCountEl.textContent = results.counts.db.motion;
        queueTempCountEl.textContent = results.counts.queue.temperature;
        queueMotionCountEl.textContent = results.counts.queue.motion;
        procTempCountEl.textContent = results.counts.processing.temperature;
        procMotionCountEl.textContent = results.counts.processing.motion;
        
        // Update missing events counts
        const missingInDb = results.missing_in_db || [];
        const missingInQueue = results.missing_in_queue || [];
        
        missingDbCountEl.textContent = `${missingInDb.length} events missing`;
        missingQueueCountEl.textContent = `${missingInQueue.length} events missing`;
        
        // Populate missing events lists
        missingDbListEl.innerHTML = '';
        missingInDb.forEach(event => {
            const eventItem = document.createElement('div');
            eventItem.className = 'event-item';
            eventItem.textContent = `Type: ${event.type}, Event ID: ${event.event_id}, Trace ID: ${event.trace_id}`;
            missingDbListEl.appendChild(eventItem);
        });
        
        missingQueueListEl.innerHTML = '';
        missingInQueue.forEach(event => {
            const eventItem = document.createElement('div');
            eventItem.className = 'event-item';
            eventItem.textContent = `Type: ${event.type}, Event ID: ${event.event_id}, Trace ID: ${event.trace_id}`;
            missingQueueListEl.appendChild(eventItem);
        });
        
    } catch (error) {
        console.error('Error fetching consistency check results:', error);
        consistencyResultsEl.style.display = 'none';
        consistencyStatusEl.innerHTML = `<p>Error fetching results: ${error.message}</p>`;
    }
}

// Add event listener for run button
runConsistencyCheckBtn.addEventListener('click', runConsistencyCheck);

// Fetch consistency check results on initial load
fetchConsistencyCheckResults();

// Add consistency check results to the periodic update function
async function updateDashboard() {
    try {
        // Existing code...
        
        // Also check for consistency results
        await fetchConsistencyCheckResults();
        
    } catch (error) {
        console.error("Error updating dashboard:", error);
    }
}

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