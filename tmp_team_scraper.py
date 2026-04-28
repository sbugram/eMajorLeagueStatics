from team_scraper import scrape_team_list, scrape_team_squad

teams = scrape_team_list()
print(f"Teams found: {len(teams)}")
if teams:
    first = teams[0]
    print(f"Scraping first team: {first['name']} @ {first['url']}")
    players = scrape_team_squad(first['name'], first['url'])
    print(f"Players scraped: {len(players)}")
    for p in players[:3]:
        print(p)
