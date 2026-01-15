# Import Flow Template for Croatian Vehicle Import Documentation

IMPORT_FLOW_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vehicle Import Process - Maritea</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
        }
        
        /* Navbar - matching admin dashboard style */
        .navbar {
            background: #2ecc71;
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .navbar-brand {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .navbar-brand img { height: 40px; }
        .navbar-brand h1 { font-size: 1.3rem; font-weight: 600; }
        .navbar-links a {
            color: white;
            text-decoration: none;
            margin-left: 20px;
            padding: 8px 16px;
            border-radius: 5px;
            transition: background 0.3s;
            font-weight: 500;
        }
        .navbar-links a:hover { background: rgba(255,255,255,0.2); }
        .navbar-links a.active { background: #27ae60; }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }
        
        /* Hero Section */
        .hero {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 30px;
        }
        .hero h1 {
            color: white;
            font-size: 2.8em;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .hero .subtitle {
            color: rgba(255,255,255,0.85);
            font-size: 1.2em;
            max-width: 700px;
            margin: 0 auto;
            line-height: 1.6;
        }
        
        /* Main Content Card */
        .content-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            margin-bottom: 30px;
        }
        
        /* Mermaid Diagram Container */
        .mermaid-container {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 30px;
            margin: 30px 0;
            overflow-x: auto;
            border: 1px solid #dee2e6;
        }
        
        /* Info Boxes */
        .info-box {
            background: #f8f9fa;
            border-left: 5px solid #2ecc71;
            padding: 25px;
            margin: 25px 0;
            border-radius: 0 10px 10px 0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .info-box:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }
        .info-box h3 {
            margin: 0 0 15px 0;
            color: #1a1a2e;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .info-box h3 .icon {
            font-size: 1.4em;
        }
        .info-box ul {
            margin: 10px 0;
            padding-left: 25px;
        }
        .info-box li {
            margin: 12px 0;
            color: #4a5568;
            line-height: 1.6;
        }
        .info-box li strong {
            color: #1a1a2e;
        }
        
        /* Documents Section - Special Styling */
        .documents-box {
            background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
            border-left: 5px solid #27ae60;
        }
        .documents-box h4 {
            color: #27ae60;
            margin: 25px 0 10px 0;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .documents-box h4:first-of-type {
            margin-top: 15px;
        }
        .documents-box p {
            color: #4a5568;
            line-height: 1.7;
            margin: 8px 0;
        }
        
        /* Critical Requirements Box */
        .critical-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-left: 5px solid #f39c12;
        }
        
        /* Phase Cards */
        .phase-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .phase-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            border-top: 4px solid #2ecc71;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .phase-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .phase-card .phase-number {
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.2em;
            margin-bottom: 15px;
        }
        .phase-card h4 {
            color: #1a1a2e;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .phase-card p {
            color: #666;
            font-size: 0.95em;
            line-height: 1.6;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 30px;
            color: rgba(255,255,255,0.7);
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }
        .footer p {
            margin: 8px 0;
        }
        .footer .tip {
            background: rgba(255,255,255,0.1);
            padding: 12px 25px;
            border-radius: 25px;
            display: inline-block;
            margin-top: 15px;
        }
        
        /* Back to Top Button */
        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #2ecc71;
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 1.5em;
            box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4);
            transition: transform 0.2s, background 0.2s;
        }
        .back-to-top:hover {
            transform: translateY(-3px);
            background: #27ae60;
        }
        
        /* Print Styles */
        @media print {
            body {
                background: white;
            }
            .navbar, .back-to-top {
                display: none;
            }
            .content-card {
                box-shadow: none;
            }
            .hero h1 {
                color: #1a1a2e;
                text-shadow: none;
            }
            .hero .subtitle {
                color: #666;
            }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .navbar {
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
            .navbar-links {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
            }
            .navbar-links a {
                margin: 5px;
            }
            .hero h1 {
                font-size: 2em;
            }
            .content-card {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-brand">
            <img src="/static/images/logo_automaritea.png" alt="Maritea Logo">
            <h1>Import Process Guide</h1>
        </div>
        <div class="navbar-links">
            <a href="/">Vehicle Search</a>
            <a href="/admin">Admin Dashboard</a>
            <a href="/import-guide" class="active">Import Guide</a>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero">
            <h1>🚗 Vehicle Import Process</h1>
            <p class="subtitle">Complete workflow for importing vehicles from EU countries into Croatia. Follow this step-by-step guide to ensure a smooth import process.</p>
        </div>
        
        <div class="content-card">
            <!-- Process Overview Cards -->
            <h2 style="color: #1a1a2e; margin-bottom: 25px; font-size: 1.5em;">📋 Process Overview</h2>
            
            <div class="phase-grid">
                <div class="phase-card">
                    <div class="phase-number">1</div>
                    <h4>Sourcing & Vetting</h4>
                    <p>Find and verify the vehicle's history, specifications, and condition before purchase.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">2</div>
                    <h4>Documentation</h4>
                    <p>Gather all required documents: invoice, registration certificate, CoC, CMR, and power of attorney.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">3</div>
                    <h4>Transport</h4>
                    <p>Arrange professional transport of the vehicle to Croatia with proper documentation.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">4</div>
                    <h4>Customs Declaration</h4>
                    <p>Report to Croatian customs office within 15 days of the invoice date.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">5</div>
                    <h4>Tax Assessment</h4>
                    <p>Calculate and pay VAT, PPMV (special motor vehicle tax), and waste management fees.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">6</div>
                    <h4>Homologation</h4>
                    <p>Complete technical inspection and homologation to verify EU compliance.</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">7</div>
                    <h4>Insurance</h4>
                    <p>Secure compulsory motor vehicle insurance (obvezno osiguranje).</p>
                </div>
                <div class="phase-card">
                    <div class="phase-number">8</div>
                    <h4>Registration</h4>
                    <p>Complete final registration and receive Croatian license plates and certificate.</p>
                </div>
            </div>
            
            <!-- Mermaid Flowchart -->
            <h2 style="color: #1a1a2e; margin: 40px 0 25px 0; font-size: 1.5em;">📊 Process Flowchart</h2>
            
            <div class="mermaid-container">
                <div class="mermaid">
graph TD
    %% Phase 1: Procurement
    Start((Start Import)) --> Sourcing[1. Sourcing & Vetting]
    Sourcing -->|Verify History/Specs| Docs[2. Gather Documentation]

    %% Phase 2: Documentation
    subgraph Documentation_Required
    Docs --> Invoice[Sales Contract / Invoice]
    Docs --> RegCert[Foreign Reg. Certificate]
    Docs --> CoC[Certificate of Conformity]
    Docs --> CMR[CMR & Power of Attorney]
    end

    %% Phase 3: Logistics & Customs
    Invoice & RegCert & CoC & CMR --> Transport[3. Transport to Croatia]
    Transport --> CustomsReport[4. Report to Customs Office<br/><i>Within 15 days of Invoice</i>]

    %% Phase 4: Taxes
    CustomsReport --> TaxProcess{Tax & Fee Assessment}
    
    subgraph Tax_Liabilities
    TaxProcess --> VAT[VAT Calculation<br/>New vs. Used Margin]
    TaxProcess --> PPMV[PPMV Declaration<br/>Age/Value/CO2]
    TaxProcess --> WasteFee[Waste Management Fee]
    end

    %% Phase 5: Technical & Registration
    VAT & PPMV & WasteFee --> Homologation[5. Homologation & Inspection]
    Homologation --> Insurance[6. Secure Compulsory Insurance]
    
    Insurance --> FinalReg[7. Final Registration]
    FinalReg --> Plates[Receive HR License Plates & Cert]
    Plates --> End((Process Complete))

    %% Formatting
    style CustomsReport fill:#f96,stroke:#333,stroke-width:2px
    style TaxProcess fill:#bbf,stroke:#333
    style End fill:#9f9,stroke:#333
                </div>
            </div>
            
            <!-- Key Process Phases -->
            <div class="info-box">
                <h3><span class="icon">📋</span> Key Process Phases</h3>
                <ul>
                    <li><strong>Phase 1-2:</strong> Procurement & Documentation - Sourcing vehicle and gathering required paperwork</li>
                    <li><strong>Phase 3-4:</strong> Logistics & Customs - Transportation and customs declaration (within 15 days)</li>
                    <li><strong>Phase 4:</strong> Tax Assessment - VAT, PPMV, and waste management fees</li>
                    <li><strong>Phase 5:</strong> Technical Compliance - Homologation, inspection, insurance, and final registration</li>
                </ul>
            </div>
            
            <!-- Critical Requirements -->
            <div class="info-box critical-box">
                <h3><span class="icon">⚠️</span> Critical Requirements</h3>
                <ul>
                    <li><strong>15-Day Deadline:</strong> Report to customs office within 15 days of invoice date</li>
                    <li><strong>Essential Documents:</strong> Sales contract, foreign registration certificate, CoC, CMR, and power of attorney (detailed below)</li>
                    <li><strong>Tax Considerations:</strong> Different VAT rules for new vs. used vehicles (margin scheme)</li>
                    <li><strong>PPMV Factors:</strong> Tax based on vehicle age, value, and CO2 emissions</li>
                </ul>
            </div>
            
            <!-- Essential Documents Explained -->
            <div class="info-box documents-box">
                <h3><span class="icon">📄</span> Essential Documents Explained</h3>
                
                <h4>📝 1. Sales Contract or Invoice (Kupoprodajni ugovor / Račun)</h4>
                <p><strong>What it is:</strong> The legal proof of purchase and transfer of ownership. If buying from a dealership, this is an Invoice; if buying from a private individual, it is a Sales Contract.</p>
                <p><strong>Why it is needed:</strong></p>
                <ul>
                    <li><strong>Customs Deadline:</strong> It establishes the "Invoice Date," which starts the 15-day countdown to report the vehicle to Croatian Customs.</li>
                    <li><strong>Tax Base:</strong> It proves the purchase price, which may be used by customs to verify the vehicle's value.</li>
                    <li><strong>VAT Status:</strong> For dealers, it must clearly state if the "Margin Scheme" (PDV na maržu) applies, which determines if you pay VAT in Croatia.</li>
                </ul>
                
                <h4>🚗 2. Foreign Registration Certificate (Prometna dozvola)</h4>
                <p><strong>What it is:</strong> The original "ID card" of the vehicle issued by the country of origin (e.g., Zulassungsbescheinigung Teil I & II in Germany).</p>
                <p><strong>Why it is needed:</strong></p>
                <ul>
                    <li><strong>De-registration:</strong> It proves the vehicle has been legally taken off the roads in the source country for export.</li>
                    <li><strong>Registration in HR:</strong> You cannot register a car in Croatia without surrendering the original foreign documents to the Croatian authorities.</li>
                    <li><strong>Verification:</strong> It confirms the vehicle's previous owners and technical status.</li>
                </ul>
                
                <h4>📋 3. Certificate of Conformity (CoC)</h4>
                <p><strong>What it is:</strong> A technical "birth certificate" issued by the manufacturer stating that the vehicle meets EU standards.</p>
                <p><strong>Why it is needed:</strong></p>
                <ul>
                    <li><strong>PPMV Tax Calculation:</strong> The CoC contains the official CO2 emission data. Since the Croatian Special Motor Vehicle Tax (PPMV) is heavily based on CO2, this document is vital for calculating how much tax you owe.</li>
                    <li><strong>Homologation:</strong> It is used by the technical station in Croatia to verify that the vehicle's technical specs (engine, tires, weights) match the EU type-approval.</li>
                    <li><strong>Note:</strong> If you don't have this, you must pay a fee to an authorized Croatian representative of the car brand to issue a "Manufacturer's Statement" (Potvrda proizvođača).</li>
                </ul>
                
                <h4>🚚 4. CMR (Consignment Note / Međunarodni tovarni list)</h4>
                <p><strong>What it is:</strong> The standardized international shipping document used for road transport.</p>
                <p><strong>Why it is needed:</strong></p>
                <ul>
                    <li><strong>Proof of Delivery:</strong> It proves the vehicle was physically moved from the seller's country to Croatia.</li>
                    <li><strong>Liability:</strong> It acts as the contract between you (the dealer) and the transport company, documenting any damage that might have occurred during transit.</li>
                    <li><strong>Tax Audits:</strong> For business accounting, the CMR is proof that the goods actually crossed the border, which is necessary to justify 0% VAT transactions between EU businesses.</li>
                </ul>
                
                <h4>✍️ 5. Power of Attorney (Punomoć)</h4>
                <p><strong>What it is:</strong> A legal document signed by the dealer authorizing another person or company to act on their behalf.</p>
                <p><strong>Why it is needed:</strong></p>
                <ul>
                    <li><strong>Transporters:</strong> It allows the truck driver to legally transport the car and handle paperwork at border checks or customs if stopped.</li>
                    <li><strong>Agency Help:</strong> If you use a specialized agency to handle the customs declaration or technical inspection in Croatia, they need a Power of Attorney to sign documents in your company's name.</li>
                    <li><strong>Efficiency:</strong> It prevents the business owner from having to be physically present at every government office during the process.</li>
                </ul>
            </div>
            
            <!-- PPMV Calculator Link -->
            <div style="text-align: center; margin: 40px 0; padding: 30px; background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); border-radius: 12px;">
                <h3 style="color: white; margin-bottom: 15px;">Need to Calculate PPMV Tax?</h3>
                <p style="color: rgba(255,255,255,0.9); margin-bottom: 20px;">Use our integrated PPMV calculator to estimate the special motor vehicle tax for your import.</p>
                <a href="/" style="display: inline-block; background: white; color: #27ae60; padding: 15px 40px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 1.1em; transition: transform 0.2s, box-shadow 0.2s;">
                    🧮 Go to Vehicle Search & PPMV Calculator
                </a>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated on: <strong>January 15, 2026</strong></p>
            <p class="tip">💡 Tip: Use browser print function (Ctrl+P) to save as PDF</p>
        </div>
    </div>
    
    <a href="#" class="back-to-top" title="Back to Top">↑</a>
    
    <script>
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }
        });
        
        // Smooth scroll for back to top
        document.querySelector('.back-to-top').addEventListener('click', function(e) {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        
        // Show/hide back to top button
        window.addEventListener('scroll', function() {
            const btn = document.querySelector('.back-to-top');
            if (window.scrollY > 300) {
                btn.style.opacity = '1';
                btn.style.pointerEvents = 'auto';
            } else {
                btn.style.opacity = '0';
                btn.style.pointerEvents = 'none';
            }
        });
    </script>
</body>
</html>
'''
