# step2_crawler.py
# All URLs verified against catalog.sjf.edu/2026-2027
# Final fixes:
#   - Criminology: flat slug /criminology/ (no school prefix)
#   - Library Media: long slug master-of-science-in-library-media-m-s

import json
import requests

BASE_URL     = "https://catalog.sjf.edu"
CATALOG_YEAR = "2026-2027"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

CATALOG_MANIFEST = {

    "school-of-arts-and-sciences": {
        "name": "School of Arts and Sciences",
        "school_url": "school/undergraduate/school-of-arts-and-sciences",
        "programs": [
            # Undergraduate Degrees
            ("Actuarial Science",                          "programs/undergraduate/school-of-arts-and-sciences/actuarial-science",                                  "undergraduate"),
            ("American Studies",                           "programs/undergraduate/school-of-arts-and-sciences/american-studies",                                   "undergraduate"),
            ("Athletic Performance",                       "programs/undergraduate/athletic-performance",                                                           "undergraduate"),
            ("Biochemistry",                               "programs/undergraduate/biochemistry",                                                                   "undergraduate"),
            ("Biology",                                    "programs/undergraduate/biology",                                                                        "undergraduate"),
            ("Chemistry",                                  "programs/undergraduate/chemistry",                                                                      "undergraduate"),
            ("Computer Science",                           "programs/undergraduate/computer-science",                                                               "undergraduate"),
            ("Criminology and Criminal Justice",           "programs/undergraduate/criminology",                                                                    "undergraduate"),  # FIXED: flat slug
            ("Cybersecurity",                              "programs/undergraduate/cybersecurity",                                                                  "undergraduate"),
            ("Data Analytics",                             "programs/undergraduate/school-of-arts-and-sciences/data-analytics",                                     "undergraduate"),
            ("Economics",                                  "programs/undergraduate/economics",                                                                      "undergraduate"),
            ("English",                                    "programs/undergraduate/english",                                                                        "undergraduate"),
            ("Film and Television",                        "programs/undergraduate/school-of-arts-and-sciences/film-and-television",                                "undergraduate"),
            ("History",                                    "programs/undergraduate/history",                                                                        "undergraduate"),
            ("Human Services",                             "programs/undergraduate/human-services-2",                                                               "undergraduate"),
            ("Interdisciplinary Studies",                  "programs/undergraduate/interdisciplinary-studies",                                                      "undergraduate"),
            ("International Studies",                      "programs/undergraduate/international-studies",                                                          "undergraduate"),
            ("Legal Studies",                              "programs/undergraduate/legal-studies",                                                                  "undergraduate"),
            ("Mathematics",                                "programs/undergraduate/school-of-arts-and-sciences/mathematics",                                        "undergraduate"),
            ("Media and Communication",                    "programs/undergraduate/school-of-arts-and-sciences/media-and-communication",                            "undergraduate"),
            ("Neuroscience and Behavior",                  "programs/undergraduate/neuroscience-and-behavior",                                                      "undergraduate"),
            ("Philosophy",                                 "programs/undergraduate/school-of-arts-and-sciences/philosophy",                                         "undergraduate"),
            ("Physics",                                    "programs/undergraduate/physics",                                                                        "undergraduate"),
            ("Political Science",                          "programs/undergraduate/political-science",                                                              "undergraduate"),
            ("Pre-Health Professions",                     "programs/undergraduate/pre-health-professions",                                                         "undergraduate"),
            ("Psychology",                                 "programs/undergraduate/psychology",                                                                     "undergraduate"),
            ("Public Health",                              "programs/undergraduate/school-of-arts-and-sciences/public-health",                                      "undergraduate"),
            ("Public Relations",                           "programs/undergraduate/school-of-arts-and-sciences/public-relations",                                   "undergraduate"),
            ("Religious Studies",                          "programs/undergraduate/religious-studies",                                                              "undergraduate"),
            ("Sociology and Anthropology",                 "programs/undergraduate/school-of-arts-and-sciences/sociology-and-anthropology",                         "undergraduate"),
            ("Spanish",                                    "programs/undergraduate/spanish",                                                                        "undergraduate"),
            ("Sport Management",                           "programs/undergraduate/sport-management",                                                               "undergraduate"),
            ("Sustainability",                             "programs/undergraduate/sustainability",                                                                 "undergraduate"),
            # Undergraduate Minors & Certificates
            ("African American Studies (Minor)",           "programs/undergraduate/african-american-studies-minor",                                                 "undergraduate"),
            ("AI Literacy (Minor)",                        "programs/undergraduate/ai-literacy-minor",                                                              "undergraduate"),
            ("Arts: Interdisciplinary Arts (Minor)",       "programs/undergraduate/school-of-arts-and-sciences/arts-interdisciplinary-arts-minor",                  "undergraduate"),
            ("Creative Writing (Minor)",                   "programs/undergraduate/school-of-arts-and-sciences/creative-writing-minor",                             "undergraduate"),
            ("Ethics (Minor)",                             "programs/undergraduate/ethics-minor",                                                                   "undergraduate"),
            ("Gender & Sexuality Studies (Minor)",         "programs/undergraduate/school-of-arts-and-sciences/gender-sexuality-studies-minor",                     "undergraduate"),
            ("Gerontology (Minor)",                        "programs/undergraduate/gerontology-minor",                                                              "undergraduate"),
            ("Global Health (Minor)",                      "programs/undergraduate/global-health-minor",                                                            "undergraduate"),
            ("Health Communication (Minor)",               "programs/undergraduate/school-of-arts-and-sciences/health-communication-minor",                         "undergraduate"),
            ("Languages and Cultures (Minor)",             "programs/undergraduate/languages-and-cultures-minor",                                                   "undergraduate"),
            ("Public and Professional Writing (Cert.)",    "programs/undergraduate/school-of-arts-and-sciences/public-and-professional-writing-certificate",        "undergraduate"),
            ("Spanish/Latino Culture for Health (Minor)",  "programs/undergraduate/school-of-arts-and-sciences/spanish-latino-culture-for-the-health-professions",  "undergraduate"),
            # Graduate
            ("Mental Health Counseling (M.S.)",            "programs/graduate/mental-health-counseling",                                                            "graduate"),
        ]
    },

    "school-of-business": {
        "name": "School of Business",
        "school_url": "school/undergraduate/school-of-business",
        "programs": [
            ("Accounting (B.S.)",                          "programs/undergraduate/accounting",                                                                     "undergraduate"),
            ("Finance (B.S.)",                             "programs/undergraduate/finance",                                                                        "undergraduate"),
            ("Healthcare Administration (B.S.)",           "programs/undergraduate/healthcare-administration",                                                      "undergraduate"),
            ("Management (B.S.)",                          "programs/undergraduate/management",                                                                     "undergraduate"),
            ("Marketing (B.S.)",                           "programs/undergraduate/marketing",                                                                      "undergraduate"),
            ("Entrepreneurship and Innovation (Minor)",    "programs/undergraduate/entrepreneurship-and-innovation-minor",                                           "undergraduate"),
            ("Professional Sales (Minor)",                 "programs/undergraduate/professional-sales-minor",                                                        "undergraduate"),
            ("Master of Business Administration (MBA)",    "programs/graduate/mba",                                                                                 "graduate"),
        ]
    },

    "school-of-education": {
        "name": "Ralph C. Wilson, Jr. School of Education",
        "school_url": "school/undergraduate/school-of-education",
        "programs": [
            # Undergraduate
            ("Inclusive Childhood Education (B.S.)",       "programs/undergraduate/school-of-education/inclusive-childhood-education",                              "undergraduate"),
            ("Inclusive Adolescence Education (B.S.)",     "programs/undergraduate/school-of-education/inclusive-adolescence-education",                            "undergraduate"),
            # Graduate — all confirmed via site search
            ("Educational Leadership (M.S.Ed.)",           "programs/graduate/school-of-education-graduate/educational-leadership",                                 "graduate"),
            ("Inclusive Childhood Education (M.S.)",       "programs/graduate/school-of-education-graduate/inclusive-childhood-education",                          "graduate"),
            ("Inclusive Adolescence Education (M.S.)",     "programs/graduate/school-of-education-graduate/inclusive-adolescence-education",                        "graduate"),
            ("Inclusive Adolescence Ed. Residency (M.S.)", "programs/graduate/school-of-education-graduate/master-of-science-in-education-inclusive-adolescence-education-residency-apprenticeship", "graduate"),
            ("Literacy Education (M.S.)",                  "programs/graduate/school-of-education-graduate/master-of-science-in-literacy-education-m-s",            "graduate"),
            ("Library Media (M.S.)",                       "programs/graduate/school-of-education-graduate/master-of-science-in-library-media-m-s",                 "graduate"),  # FIXED: long slug
            ("Executive Leadership (Ed.D.)",               "programs/graduate/school-of-education-graduate/edd",                                                    "graduate"),
        ]
    },

    "school-of-nursing": {
        "name": "Wegmans School of Nursing",
        "school_url": "school/undergraduate/school-of-nursing",
        "programs": [
            # Undergraduate
            ("Nursing B.S. (Traditional)",                 "programs/undergraduate/school-of-nursing/traditional-nursing",                                          "undergraduate"),
            ("RN to B.S.N. (Online)",                      "programs/undergraduate/school-of-nursing/rn-to-bsn",                                                   "undergraduate"),
            # Graduate
            ("Nursing (M.S.)",                             "programs/graduate/school-of-nursing-graduate/nursing",                                                  "graduate"),
            ("Mental Health Counseling (M.S.)",            "programs/graduate/school-of-nursing-graduate/mental-health-counseling",                                 "graduate"),
            ("DNP Post Masters & Post Baccalaureate",      "programs/graduate/school-of-nursing-graduate/dnp",                                                      "graduate"),
            ("DNP Nurse Anesthesia / AGACNP",              "programs/graduate/school-of-nursing-graduate/doctor-of-nursing-practice-in-nurse-anesthesia-and-adult-gerontology-acute-care-nurse-practitioner-agacnp", "graduate"),
        ]
    },

    "school-of-pharmacy": {
        "name": "Wegmans School of Pharmacy",
        "school_url": "school/undergraduate/school-of-pharmacy",
        "programs": [
            ("Pre-Pharmacy",                               "programs/undergraduate/pre-pharmacy",                                                                   "undergraduate"),
            ("Doctor of Pharmacy (Pharm.D.)",              "programs/graduate/pharmacy",                                                                            "graduate"),
            ("Doctor of Pharmacy / MBA",                   "programs/graduate/pharmacy-mba",                                                                        "graduate"),
        ]
    },
}


def verify_url(url):
    """HEAD request — returns True if URL resolves to 200."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False


def main():
    print(f"Building catalog map for {CATALOG_YEAR}...\n")

    catalog_data = {
        "catalog_year": CATALOG_YEAR,
        "schools": []
    }

    total_verified  = 0
    total_not_found = 0
    not_found_list  = []

    for school_slug, school_info in CATALOG_MANIFEST.items():
        school_name = school_info["name"]
        print(f"\n🏫 {school_name}")

        by_level = {}
        for (prog_name, url_path, level) in school_info["programs"]:
            by_level.setdefault(level, []).append((prog_name, url_path))

        school_entry = {
            "name":   school_name,
            "slug":   school_slug,
            "url":    f"{BASE_URL}/{CATALOG_YEAR}/{school_info['school_url']}/",
            "levels": []
        }

        for level in ["undergraduate", "graduate"]:
            if level not in by_level:
                continue

            school_level_url = f"{BASE_URL}/{CATALOG_YEAR}/school/{level}/{school_slug}/"
            programs = []

            for (prog_name, url_path) in by_level[level]:
                full_url = f"{BASE_URL}/{CATALOG_YEAR}/{url_path}/"
                exists   = verify_url(full_url)
                status   = "✅" if exists else "❌ NOT FOUND"

                if exists:
                    total_verified += 1
                    slug = url_path.rstrip("/").split("/")[-1]
                    programs.append({
                        "name": prog_name,
                        "slug": slug,
                        "url":  full_url,
                    })
                else:
                    total_not_found += 1
                    not_found_list.append((school_name, level, prog_name, full_url))

                print(f"   [{level[:4].upper()}] {status} {prog_name}")

            school_entry["levels"].append({
                "level":    level.capitalize(),
                "url":      school_level_url,
                "programs": programs
            })

        catalog_data["schools"].append(school_entry)

    with open("catalog_map.json", "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Verified:   {total_verified} programs")
    print(f"❌ Not found:  {total_not_found} programs")

    if not_found_list:
        print(f"\nPrograms needing slug correction:")
        for (school, level, name, url) in not_found_list:
            print(f"  [{level[:4].upper()}] {school} | {name}")
            print(f"         Tried: {url}")

    print(f"\n📄 Saved to: catalog_map.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
