source("hyperrank.R")

d1 <- list(
  doc_id=paste("https://www.washingtonpost.com/world/europe",
               "julian-assange-expelled-from-his-embassy-perch-will-fight-extradition-from-jail",
               "2019/04/12/d388584c-5cb2-11e9-98d4-844088d135f2_story.html", sep="/"),
  title="Julian Assange, expelled from his embassy perch, will fight extradition from jail",
  text=paste("Julian Assange arrives at Westminster Magistrates' Court in London",
             "after the WikiLeaks founder was arrested by Metropolitan Police officers on Thursday April 11, 2019."),
  entities=list(
    list(label="Julian Assange",
         uri="https://en.wikipedia.org/wiki/Julian_Assange"),
    list(label="Westminster Magistrates' Court",
         uri="https://en.wikipedia.org/wiki/Westminster_Magistrates%27_Court"),
    list(label="London",
         uri="https://en.wikipedia.org/wiki/London"),
    list(label="WikiLeaks",
         uri="https://en.wikipedia.org/wiki/WikiLeaks"),
    list(label="Metropolitan Police Service",
         uri="https://en.wikipedia.org/wiki/Metropolitan_Police_Service"),
    list(label="April 2019",
         uri="https://en.wikipedia.org/wiki/April_2019")
  ),
  triples=list(
    list(
      list(label="Julian Assange",
           uri="https://en.wikipedia.org/wiki/Julian_Assange"),
      list(label="creator"),
      list(label="WikiLeaks",
           uri="https://en.wikipedia.org/wiki/WikiLeaks")
    ),
    list(
      list(label="Westminster Magistrates' Court",
           uri="https://en.wikipedia.org/wiki/Westminster_Magistrates%27_Court"),
      list(label="location"),
      list(label="London",
           uri="https://en.wikipedia.org/wiki/London")
    )
  )
)

d2 <- list(
  doc_id="https://kotaku.com/trading-steam-for-the-epic-games-store-creates-more-pro-1833976563",
  title="Trading Steam for the Epic Games Store Creates More Problems",
  text=paste("The Epic Games Store has a surprising amount of exclusives coming over to their platform",
             "that used to be on the default one-stop shop on PC: Steam. And everyone lived happily ever after.",
             "Oh wait, actually, it led to Steam users “review-bombing” games like Borderlands 3 and",
             "Metro Exodus after they went to the Epic store. The bigger concern here is the whole idea of games",
             "that are exclusive to just one platform, and whether our game libraries really belong to us or not."),
  entities=list(
    list(label="Epic Games Store",
         uri="https://en.wikipedia.org/wiki/Epic_Games_Store"),
    list(label="Platform",
         uri="https://en.wikipedia.org/wiki/Computing_platform"),
    list(label="PC",
         uri="https://en.wikipedia.org/wiki/Personal_computer"),
    list(label="Steam",
         uri="https://en.wikipedia.org/wiki/Steam_(software)"),
    list(label="Review Bombing",
         uri="https://en.wikipedia.org/wiki/Review_bomb"),
    list(label="Borderlands 3",
         uri="https://en.wikipedia.org/wiki/Borderlands_3"),
    list(label="Metro Exodus",
         uri="https://en.wikipedia.org/wiki/Metro_Exodus")
  ),
  triples=list(
    list(
      list(label="Steam",
           uri="https://en.wikipedia.org/wiki/Steam_(software)"),
      list(label="review"),
      list(label="Borderlands 3",
           uri="https://en.wikipedia.org/wiki/Borderlands_3")
    ),
    list(
      list(label="Steam",
           uri="https://en.wikipedia.org/wiki/Steam_(software)"),
      list(label="review"),
      list(label="Metro Exodus",
           uri="https://en.wikipedia.org/wiki/Metro_Exodus")
    )
  )
)

d3 <- list(
  doc_id="https://www.gamesindustry.biz/articles/2019-04-03-mayor-sadiq-khan-opens-london-games-festival-2019",
  title="Mayor Sadiq Khan opens London Games Festival 2019",
  text=paste("The Mayor of London was the guest of honour at last night's launch party",
             "for this year's London Games Festival."),
  entities=list(
    list(label="Mayor of London",
         uri="https://en.wikipedia.org/wiki/Mayor_of_London"),
    list(label="London",
         uri="https://en.wikipedia.org/wiki/London"),
    list(label="London Games Festival",
         uri="https://en.wikipedia.org/wiki/London_Games_Festival")
  ),
  triples=list(
    list(
      list(label="Mayor of London",
           uri="https://en.wikipedia.org/wiki/Mayor_of_London"),
      list(label="guest"),
      list(label="London Games Festival",
           uri="https://en.wikipedia.org/wiki/London_Games_Festival")
    )
  )
)

D <- list(d1, d2, d3)

idx <- open_index("/tmp/hyperrank")
print(idx)
index_batch(D[1:2])
index_batch(D[3])
