# Add this to your app.py file

@app.route('/admin/populate-counties')
def populate_all_counties():
    """Admin endpoint to populate all US counties"""
    try:
        # Sample of major counties for each state - this is a simplified version
        all_counties = {
            "AL": ["Autauga", "Baldwin", "Barbour", "Bibb", "Blount", "Bullock", "Butler", "Calhoun", "Chambers", "Cherokee", "Chilton", "Choctaw", "Clarke", "Clay", "Cleburne", "Coffee", "Colbert", "Conecuh", "Coosa", "Covington", "Crenshaw", "Cullman", "Dale", "Dallas", "DeKalb", "Elmore", "Escambia", "Etowah", "Fayette", "Franklin", "Geneva", "Greene", "Hale", "Henry", "Houston", "Jackson", "Jefferson", "Lamar", "Lauderdale", "Lawrence", "Lee", "Limestone", "Lowndes", "Macon", "Madison", "Marengo", "Marion", "Marshall", "Mobile", "Monroe", "Montgomery", "Morgan", "Perry", "Pickens", "Pike", "Randolph", "Russell", "St. Clair", "Shelby", "Sumter", "Talladega", "Tallapoosa", "Tuscaloosa", "Walker", "Washington", "Wilcox", "Winston"],
            "AK": ["Aleutians East", "Aleutians West", "Anchorage", "Bethel", "Bristol Bay", "Denali", "Dillingham", "Fairbanks North Star", "Haines", "Hoonah-Angoon", "Juneau", "Kenai Peninsula", "Ketchikan Gateway", "Kodiak Island", "Lake and Peninsula", "Matanuska-Susitna", "Nome", "North Slope", "Northwest Arctic", "Petersburg", "Prince of Wales-Hyder", "Sitka", "Skagway", "Southeast Fairbanks", "Valdez-Cordova", "Wade Hampton", "Wrangell", "Yakutat", "Yukon-Koyukuk"],
            "DE": ["New Castle", "Kent", "Sussex"],
            # Add more states as needed...
        }
        
        added_count = 0
        for state_abbr, counties in all_counties.items():
            state = State.query.filter_by(abbreviation=state_abbr).first()
            if state:
                for county_name in counties:
                    # Check if county already exists
                    existing = County.query.filter_by(name=county_name, state_id=state.id).first()
                    if not existing:
                        county = County(name=county_name, state_id=state.id)
                        db.session.add(county)
                        added_count += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Added {added_count} new counties",
            "total_counties": County.query.count()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
