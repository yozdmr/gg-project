from utils.helpers.award_merging import merge_similar_awards_second_pass, normalize_award_name, find_award_subsets

def test_second_pass_merging():
    # Test data with various cases that should be merged
    test_awards = {
        "best actor in a motion picture": 607.40,
        "best supporting actor": 518.80,
        "Best Director": 466.90,
        "best actor": 334.70,
        "best original song": 214.30,
        "Best Actress": 205.90,
        "Best Supporting Actress in a Motion Picture": 186.00,
        "Best Actor Motion Picture - Drama": 161.90,
        "Best Actress Motion Picture - Comedy or Musical": 158.00,
        "best screenplay": 150.50,
        "best actress in a comedy or musical movie": 119.40,
        "Best Original Song Motion Picture award": 119.30,
        "Best Actress in a Miniseries or TV Movie": 101.70,
        "best song": 100.90,
        "best actor in a drama": 90.30,
        "Best Motion Picture": 67.20,
        "Best Animated Film - great year": 63.60,
        "best actor in miniseries": 62.90,
        "Best Actor in a Miniseries or Motion Picture Made for Television": 59.20,
        "Best Director Golden Globe": 57.20,
        "best film director": 50.60,
        "best motion picture screenplay": 49.60,
        "best actress in a drama": 49.00,
        "best actress in a comedy": 46.30,
        "best actor in a tv comedy or musical": 42.20,
        "Best Director - Motion Picture": 39.60,
        "best actor in a comedy or musical TV series": 39.00,
        "best actress in TV drama": 35.80,
        "Best Supporting Actress - TV": 35.20,
        "Best Original Screenplay": 32.30,
        "best score": 32.20,
        "Best Actress in a Comedy Series": 29.60,
        "best actress in a TV series drama": 25.90,
        "Best Actor In a Motion Picture - Comedy Or Musical": 25.60,
        "Best Actor Academy Award": 25.00,
        "Best Drama TV Actress": 25.00,
        "Best Original Score": 20.70,
        "Best Actress in a TV Series": 20.20,
        "best actress in a musical comedy": 19.10,
        "Best Actor in a Television Series": 19.00,
    }
    
    print("Before second-pass merging:")
    print("=" * 50)
    for award, weight in sorted(test_awards.items(), key=lambda x: -x[1]):
        print(f"{weight:5.2f} - {award}")
    
    # Debug: Show normalization
    print("\nDebug - Normalized names:")
    print("=" * 50)
    for award in test_awards.keys():
        normalized = normalize_award_name(award)
        print(f"'{award}' -> '{normalized}'")
    
    # Debug: Show subset relationships
    print("\nDebug - Subset relationships:")
    print("=" * 50)
    subset_map = find_award_subsets(test_awards)
    for award, parents in subset_map.items():
        if parents:
            print(f"'{award}' fits into: {parents}")
    
    print("\nAfter second-pass merging:")
    print("=" * 50)
    merged_awards = merge_similar_awards_second_pass(test_awards)
    
    for award, weight in sorted(merged_awards.items(), key=lambda x: -x[1]):
        print(f"{weight:5.2f} - {award}")
    
    print(f"\nReduced from {len(test_awards)} to {len(merged_awards)} awards")

if __name__ == "__main__":
    test_second_pass_merging()
