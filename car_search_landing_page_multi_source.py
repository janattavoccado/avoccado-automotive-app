"""
AutoMaritea & AutoScout24 Car Search Landing Page with Multi-Source Support
HTML form for searching vehicles from multiple sources with Create Offer feature

File location: pareto_agents/car_search_landing_page.py
"""


def render_car_search_page():
    """
    Render the car search landing page with multi-source support
    
    Returns:
        str: HTML content
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vehicle Search & Offers - AutoMaritea & AutoScout24</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                max-width: 700px;
                width: 100%;
                padding: 40px;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .header h1 {
                color: #333;
                font-size: 28px;
                margin-bottom: 10px;
            }
            
            .header p {
                color: #666;
                font-size: 14px;
            }
            
            .logo {
                font-size: 24px;
                color: #667eea;
                margin-bottom: 10px;
                font-weight: bold;
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                color: #333;
                font-weight: 500;
                font-size: 14px;
            }
            
            input[type="text"],
            input[type="email"],
            input[type="number"],
            select {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                font-family: inherit;
                transition: border-color 0.3s;
            }
            
            input[type="text"]:focus,
            input[type="email"]:focus,
            input[type="number"]:focus,
            select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            
            .form-row.full {
                grid-template-columns: 1fr;
            }
            
            .checkbox-group {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }
            
            input[type="checkbox"] {
                width: 18px;
                height: 18px;
                cursor: pointer;
            }
            
            .checkbox-group label {
                margin: 0;
                cursor: pointer;
            }
            
            .sources-section {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border: 1px solid #ddd;
            }
            
            .sources-title {
                font-weight: 600;
                color: #333;
                margin-bottom: 12px;
                font-size: 14px;
            }
            
            .sources-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            
            .source-checkbox {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 10px;
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .source-checkbox:hover {
                background: #e7f3ff;
                border-color: #667eea;
            }
            
            .source-checkbox input[type="checkbox"] {
                width: 16px;
                height: 16px;
                margin: 0;
            }
            
            .source-checkbox label {
                margin: 0;
                cursor: pointer;
                font-size: 13px;
                flex: 1;
            }
            
            .button-group {
                display: flex;
                gap: 10px;
                margin-top: 30px;
            }
            
            button {
                flex: 1;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .btn-search {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .btn-search:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            
            .btn-search:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .btn-clear {
                background: #f0f0f0;
                color: #333;
            }
            
            .btn-clear:hover {
                background: #e0e0e0;
            }
            
            .btn-create-offer {
                background: #28a745;
                color: white;
            }
            
            .btn-create-offer:hover {
                background: #218838;
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(40, 167, 69, 0.4);
            }
            
            .btn-back {
                background: #6c757d;
                color: white;
            }
            
            .btn-back:hover {
                background: #5a6268;
            }
            
            .loading {
                display: none;
                text-align: center;
                margin-top: 20px;
            }
            
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .message {
                padding: 12px;
                border-radius: 5px;
                margin-top: 15px;
                display: none;
            }
            
            .message.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .message.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .info-box {
                background: #e7f3ff;
                border-left: 4px solid #667eea;
                padding: 12px;
                margin-bottom: 20px;
                border-radius: 3px;
                font-size: 13px;
                color: #0066cc;
            }
            
            /* Results Preview Section */
            .results-section {
                display: none;
                margin-top: 30px;
            }
            
            .results-section.show {
                display: block;
            }
            
            .results-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid #667eea;
            }
            
            .results-header h2 {
                color: #333;
                font-size: 20px;
            }
            
            .results-count {
                background: #667eea;
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
            }
            
            .car-list {
                max-height: 500px;
                overflow-y: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            
            .car-item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            .car-item:last-child {
                border-bottom: none;
            }
            
            .car-item:hover {
                background: #f8f9fa;
            }
            
            .car-item.selected {
                background: #e7f3ff;
                border-left: 4px solid #667eea;
            }
            
            .car-title {
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
                font-size: 15px;
            }
            
            .car-source {
                display: inline-block;
                font-size: 11px;
                background: #667eea;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                margin-bottom: 8px;
            }
            
            .car-details {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                font-size: 13px;
                color: #666;
            }
            
            .car-detail {
                display: flex;
                justify-content: space-between;
            }
            
            .car-detail-label {
                font-weight: 500;
            }
            
            .car-detail-value {
                color: #333;
            }
            
            .car-link {
                display: inline-block;
                margin-top: 8px;
                color: #667eea;
                text-decoration: none;
                font-size: 12px;
            }
            
            .car-link:hover {
                text-decoration: underline;
            }
            
            .offer-form {
                display: none;
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 5px;
            }
            
            .offer-form.show {
                display: block;
            }
            
            .offer-form h3 {
                color: #333;
                margin-bottom: 15px;
                font-size: 18px;
            }
            
            .offer-fields {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
            }
            
            .offer-fields.full {
                grid-template-columns: 1fr;
            }
            
            .offer-field {
                display: flex;
                flex-direction: column;
            }
            
            .offer-field label {
                margin-bottom: 8px;
                font-weight: 500;
                color: #333;
                font-size: 14px;
            }
            
            .offer-field input,
            .offer-field textarea {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: inherit;
                font-size: 14px;
            }
            
            .offer-field textarea {
                resize: vertical;
                min-height: 100px;
            }
            
            .offer-field input:focus,
            .offer-field textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .offer-button-group {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            
            @media (max-width: 600px) {
                .container {
                    padding: 20px;
                }
                
                .form-row {
                    grid-template-columns: 1fr;
                }
                
                .sources-grid {
                    grid-template-columns: 1fr;
                }
                
                .offer-fields {
                    grid-template-columns: 1fr;
                }
                
                .header h1 {
                    font-size: 24px;
                }
                
                .button-group {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Search Form Section -->
            <div id="searchSection">
                <div class="header">
                    <div class="logo">🚗 Vehicle Search</div>
                    <h1>Find & Create Offers</h1>
                    <p>Search AutoMaritea and AutoScout24 for vehicles</p>
                </div>
                
                <div class="info-box">
                    ℹ️ Search vehicles from multiple sources. Check "Create Offer" to select a car and create a professional offer.
                </div>
                
                <form id="searchForm">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="brand">Brand</label>
                            <input type="text" id="brand" name="brand" placeholder="e.g., Mercedes-Benz, BMW, Audi" />
                        </div>
                        <div class="form-group">
                            <label for="model">Model</label>
                            <input type="text" id="model" name="model" placeholder="e.g., C-klasa, 3 Series" />
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="minYear">Year From</label>
                            <input type="number" id="minYear" name="minYear" placeholder="e.g., 2015" min="1990" max="2030" />
                        </div>
                        <div class="form-group">
                            <label for="maxPrice">Max Price (€)</label>
                            <input type="number" id="maxPrice" name="maxPrice" placeholder="e.g., 50000" min="0" />
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="maxMileage">Max Mileage (km)</label>
                            <input type="number" id="maxMileage" name="maxMileage" placeholder="e.g., 150000" min="0" />
                        </div>
                        <div class="form-group">
                            <label for="fuelType">Fuel Type</label>
                            <select id="fuelType" name="fuelType">
                                <option value="">-- Select --</option>
                                <option value="petrol">Petrol</option>
                                <option value="diesel">Diesel</option>
                                <option value="hybrid">Hybrid</option>
                                <option value="electric">Electric</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-row full">
                        <div class="form-group">
                            <label for="email">Your Email</label>
                            <input type="email" id="email" name="email" placeholder="your@email.com" required />
                        </div>
                    </div>
                    
                    <!-- Search Sources Selection -->
                    <div class="sources-section">
                        <div class="sources-title">📍 Search Sources</div>
                        <div class="sources-grid">
                            <div class="source-checkbox">
                                <input type="checkbox" id="sourceAutomaritea" name="sources" value="automaritea" checked />
                                <label for="sourceAutomaritea">AutoMaritea (Croatia)</label>
                            </div>
                            <div class="source-checkbox">
                                <input type="checkbox" id="sourceAutoscout24" name="sources" value="autoscout24" checked />
                                <label for="sourceAutoscout24">AutoScout24 (Europe)</label>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Create Offer Checkbox -->
                    <div class="checkbox-group">
                        <input type="checkbox" id="createOffer" name="createOffer" />
                        <label for="createOffer">Create Offer - Select a car from results to create a professional offer</label>
                    </div>
                    
                    <div class="button-group">
                        <button type="submit" class="btn-search" id="searchBtn">🔍 Search Vehicles</button>
                        <button type="reset" class="btn-clear">Clear</button>
                    </div>
                    
                    <div class="loading" id="loading">
                        <div class="spinner"></div>
                        <p>Searching vehicles...</p>
                    </div>
                    
                    <div class="message" id="message"></div>
                </form>
            </div>
            
            <!-- Results Section (shown when Create Offer is checked) -->
            <div id="resultsSection" class="results-section">
                <div class="results-header">
                    <h2>Available Vehicles</h2>
                    <div class="results-count" id="resultsCount">0 vehicles</div>
                </div>
                <div class="car-list" id="carList"></div>
            </div>
            
            <!-- Offer Form Section -->
            <div id="offerSection" class="offer-form">
                <h3>📧 Create Offer</h3>
                <form id="offerForm">
                    <div class="offer-fields">
                        <div class="offer-field">
                            <label for="clientName">Client Name *</label>
                            <input type="text" id="clientName" name="clientName" required />
                        </div>
                        <div class="offer-field">
                            <label for="clientEmail">Client Email *</label>
                            <input type="email" id="clientEmail" name="clientEmail" required />
                        </div>
                    </div>
                    
                    <div class="offer-fields full">
                        <div class="offer-field">
                            <label for="companyName">Company Name</label>
                            <input type="text" id="companyName" name="companyName" placeholder="Your company name" />
                        </div>
                    </div>
                    
                    <div class="offer-fields">
                        <div class="offer-field">
                            <label for="salesAgent">Sales Agent Name</label>
                            <input type="text" id="salesAgent" name="salesAgent" placeholder="Your name" />
                        </div>
                        <div class="offer-field">
                            <label for="phone">Phone Number</label>
                            <input type="text" id="phone" name="phone" placeholder="Your phone" />
                        </div>
                    </div>
                    
                    <div class="offer-fields">
                        <div class="offer-field">
                            <label for="agentEmail">Your Email</label>
                            <input type="email" id="agentEmail" name="agentEmail" placeholder="your@company.com" />
                        </div>
                        <div class="offer-field">
                            <label for="condition">Vehicle Condition</label>
                            <input type="text" id="condition" name="condition" placeholder="e.g., Excellent, Good, Fair" />
                        </div>
                    </div>
                    
                    <div class="offer-fields full">
                        <div class="offer-field">
                            <label for="features">Key Features (one per line)</label>
                            <textarea id="features" name="features" placeholder="• Feature 1&#10;• Feature 2&#10;• Feature 3"></textarea>
                        </div>
                    </div>
                    
                    <div class="offer-button-group">
                        <button type="submit" class="btn-create-offer">📧 Send Offer</button>
                        <button type="button" class="btn-back" id="backBtn">← Back to Search</button>
                    </div>
                    
                    <div class="message" id="offerMessage"></div>
                </form>
            </div>
        </div>
        
        <script>
            // State management
            let searchResults = [];
            let selectedCar = null;
            let createOfferMode = false;
            
            // Elements
            const searchForm = document.getElementById('searchForm');
            const createOfferCheckbox = document.getElementById('createOffer');
            const resultsSection = document.getElementById('resultsSection');
            const carList = document.getElementById('carList');
            const resultsCount = document.getElementById('resultsCount');
            const offerSection = document.getElementById('offerSection');
            const offerForm = document.getElementById('offerForm');
            const backBtn = document.getElementById('backBtn');
            const loading = document.getElementById('loading');
            const message = document.getElementById('message');
            const offerMessage = document.getElementById('offerMessage');
            const searchBtn = document.getElementById('searchBtn');
            
            // Toggle Create Offer mode
            createOfferCheckbox.addEventListener('change', (e) => {
                createOfferMode = e.target.checked;
            });
            
            // Back button
            backBtn.addEventListener('click', () => {
                offerSection.classList.remove('show');
                resultsSection.classList.add('show');
                selectedCar = null;
            });
            
            // Search form submission
            searchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const email = document.getElementById('email').value.trim();
                if (!email) {
                    showMessage('Please enter your email address', 'error');
                    return;
                }
                
                // Get selected sources
                const sources = Array.from(document.querySelectorAll('input[name="sources"]:checked'))
                    .map(cb => cb.value);
                
                if (sources.length === 0) {
                    showMessage('Please select at least one search source', 'error');
                    return;
                }
                
                // Collect form data
                const formData = new FormData(searchForm);
                const data = {
                    brand: formData.get('brand') || null,
                    model: formData.get('model') || null,
                    minYear: formData.get('minYear') ? parseInt(formData.get('minYear')) : null,
                    maxPrice: formData.get('maxPrice') ? parseInt(formData.get('maxPrice')) : null,
                    maxMileage: formData.get('maxMileage') ? parseInt(formData.get('maxMileage')) : null,
                    fuelType: formData.get('fuelType') || null,
                    email: email,
                    create_offer: createOfferMode,
                    sources: sources
                };
                
                // Show loading
                loading.style.display = 'block';
                searchBtn.disabled = true;
                message.style.display = 'none';
                
                try {
                    const response = await fetch('/api/car-search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        if (createOfferMode) {
                            // Get search results and display them
                            searchResults = result.listings || [];
                            if (searchResults.length > 0) {
                                displayResults(searchResults);
                                resultsSection.classList.add('show');
                                showMessage('✅ Search completed! Select a vehicle to create an offer.', 'success');
                            } else {
                                showMessage('❌ No vehicles found matching your criteria.', 'error');
                            }
                        } else {
                            showMessage('✅ Search completed! Results sent to your email.', 'success');
                            searchForm.reset();
                            createOfferCheckbox.checked = false;
                            createOfferMode = false;
                        }
                    } else {
                        showMessage('❌ Error: ' + (result.error || result.message || 'Unknown error'), 'error');
                    }
                } catch (error) {
                    showMessage('❌ Error: ' + error.message, 'error');
                } finally {
                    loading.style.display = 'none';
                    searchBtn.disabled = false;
                }
            });
            
            // Display search results
            function displayResults(results) {
                carList.innerHTML = '';
                resultsCount.textContent = results.length + ' vehicle' + (results.length !== 1 ? 's' : '');
                
                results.forEach((car, index) => {
                    const carItem = document.createElement('div');
                    carItem.className = 'car-item';
                    
                    // Determine source
                    const source = car.seller_type ? 'AutoScout24' : 'AutoMaritea';
                    
                    carItem.innerHTML = `
                        <div class="car-source">${source}</div>
                        <div class="car-title">${car.title || 'Vehicle'}</div>
                        <div class="car-details">
                            <div class="car-detail">
                                <span class="car-detail-label">Price:</span>
                                <span class="car-detail-value">${car.price || 'N/A'}</span>
                            </div>
                            <div class="car-detail">
                                <span class="car-detail-label">Year:</span>
                                <span class="car-detail-value">${car.year || 'N/A'}</span>
                            </div>
                            <div class="car-detail">
                                <span class="car-detail-label">Mileage:</span>
                                <span class="car-detail-value">${car.mileage || 'N/A'}</span>
                            </div>
                            <div class="car-detail">
                                <span class="car-detail-label">Fuel:</span>
                                <span class="car-detail-value">${car.fuel_type || 'N/A'}</span>
                            </div>
                        </div>
                        <a href="${car.url}" target="_blank" class="car-link">View Listing →</a>
                    `;
                    
                    carItem.addEventListener('click', () => {
                        selectCar(car, carItem);
                    });
                    
                    carList.appendChild(carItem);
                });
            }
            
            // Select a car for offer
            function selectCar(car, element) {
                // Remove previous selection
                document.querySelectorAll('.car-item').forEach(item => {
                    item.classList.remove('selected');
                });
                
                // Select new car
                element.classList.add('selected');
                selectedCar = car;
                
                // Populate offer form with car data
                populateOfferForm(car);
                
                // Show offer form
                resultsSection.classList.remove('show');
                offerSection.classList.add('show');
            }
            
            // Populate offer form with car data
            function populateOfferForm(car) {
                // Pre-fill with car data where applicable
                document.getElementById('condition').value = 'Excellent';
                
                // Pre-fill features if available
                let features = '• Well-maintained vehicle\\n• Full service history\\n• Clean interior and exterior';
                if (car.features) {
                    features = car.features;
                }
                document.getElementById('features').value = features;
            }
            
            // Submit offer form
            offerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                if (!selectedCar) {
                    showOfferMessage('Please select a vehicle first', 'error');
                    return;
                }
                
                const offerData = {
                    car: selectedCar,
                    client_name: document.getElementById('clientName').value,
                    client_email: document.getElementById('clientEmail').value,
                    company_name: document.getElementById('companyName').value,
                    sales_agent_name: document.getElementById('salesAgent').value,
                    phone_number: document.getElementById('phone').value,
                    agent_email: document.getElementById('agentEmail').value,
                    condition: document.getElementById('condition').value,
                    features: document.getElementById('features').value
                };
                
                try {
                    const response = await fetch('/api/create-offer', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(offerData)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showOfferMessage('✅ Offer sent successfully to ' + offerData.client_email, 'success');
                        setTimeout(() => {
                            // Reset and go back to search
                            offerForm.reset();
                            offerSection.classList.remove('show');
                            searchForm.reset();
                            createOfferCheckbox.checked = false;
                            createOfferMode = false;
                            selectedCar = null;
                        }, 2000);
                    } else {
                        showOfferMessage('❌ Error: ' + (result.error || result.message || 'Failed to send offer'), 'error');
                    }
                } catch (error) {
                    showOfferMessage('❌ Error: ' + error.message, 'error');
                }
            });
            
            function showMessage(text, type) {
                message.textContent = text;
                message.className = 'message ' + type;
                message.style.display = 'block';
            }
            
            function showOfferMessage(text, type) {
                offerMessage.textContent = text;
                offerMessage.className = 'message ' + type;
                offerMessage.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return html
