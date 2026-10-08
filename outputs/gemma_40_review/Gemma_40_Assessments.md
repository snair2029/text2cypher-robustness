# Gemma same-40 assessments for final verification

All 40 assessments below are proposals from query inspection, schema and saved evidence. Student decisions remain pending. No new database execution was performed.

## 1. instance_id_35775
Which organizations have a parent organization with a higher revenue?

Gemma query:
```cypher
MATCH (parent:Organization)-[:HAS_SUBSIDIARY]->(child:Organization)
WHERE parent.revenue > child.revenue
RETURN child
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Gemma uses the declared parent-to-subsidiary direction, filters higher parent revenue and returns the requested child organisations. Extra reference columns are optional. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 2. instance_id_2789
Find all 'Vehicle Crime' crimes

Gemma query:
```cypher
MATCH (c:Crime) WHERE c.type = 'Vehicle Crime' RETURN c
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Exact Vehicle Crime equality differs from reference case-insensitive comparison. Stored capitalization and the required matching policy are unavailable; no database check was possible. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 3. instance_id_5551
Look for the report_no of the Report that is not related  to the Article with the  comments  19 pages, AMSLatex, references added!

Gemma query:
```cypher
MATCH (a:Article {comments: '19 pages, AMSLatex, references added!'}) MATCH (r:Report) WHERE NOT (r)-[]-(a) RETURN r.report_no
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma excludes relationships to the specifically selected Article; reference excludes outgoing links to any Article and leaves the selected Article unbound. Exclamation-mark literal and intended direction remain ambiguous. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 4. instance_id_29896
Which organization has the most subsidiaries?

Gemma query:
```cypher
MATCH (o:Organization)-[:HAS_SUBSIDIARY]->(:Organization)
RETURN o.name
ORDER BY count(*) DESC
LIMIT 1
```

Syntax: error_present; schema: no_error_identified; logical: uncertain; reference: no_issue_identified.

Saved Neo4j syntax validation rejected this query. Names and relationship are declared, but aggregation in ORDER BY is not successfully planned; no separate semantic correctness judgement is possible. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 5. instance_id_16495
Find nodes that share a relationship with both Keyword and Keyword!

Gemma query:
```cypher
MATCH (n)-[]-(k1:Keyword), (n)-[]-(k2:Keyword) WHERE k1 <> k2 RETURN n
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Gemma requires two distinct Keyword neighbours in either direction and returns nodes; reference requires outgoing connections and returns labels. The repeated Keyword wording does not resolve distinctness or direction. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 6. instance_id_6067
Find nodes that are at the end of a path starting at Keyword where name is log-balanced and traversing through Author with author_id befdd60b44b9cd4d5ffc084ce31d92d4!

Gemma query:
```cypher
MATCH (k:Keyword {name: 'log-balanced'})-->(a:Author {author_id: 'befdd60b44b9cd4d5ffc084ce31d92d4'})-->(n) RETURN n
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Gemma permits exactly one hop to Author and one hop onwards; reference permits variable-length paths on both segments. Intended path length is unspecified and source graph unavailable. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 7. instance_id_24738
Which 3 movies have the highest IMDb votes?

Gemma query:
```cypher
MATCH (m:Movie)
RETURN m.title
ORDER BY m.imdbVotes DESC
LIMIT 3
```

Syntax: no_error_identified; schema: no_error_identified; logical: error_present; reference: no_issue_identified.

Under the recorded highest-known-votes rule, Gemma omits the non-null IMDb-vote filter before descending ranking. Unknown votes can outrank known values. Titles are an acceptable projection; saved outputs differ. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 8. instance_id_42155
List the top 5 oldest directors in the database.

Gemma query:
```cypher
MATCH (d:Director)
RETURN d.name
ORDER BY d.born ASC
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Same Director population, birth-date ascending order and limit five. Director names satisfy the list request. Tie handling is unspecified in both; judgement is limited to query inspection. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 9. instance_id_30819
What is the average unit price of products in orders shipped to 'Denmark'?

Gemma query:
```cypher
MATCH (o:Order)-[r:ORDERS]->(p:Product)
WHERE o.shipCountry = 'Denmark'
RETURN avg(toFloat(r.unitPrice))
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma averages the declared ORDERS.unitPrice property; reference reads undeclared Order.unitPrice. Transaction versus product-catalogue price and averaging unit remain ambiguous. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 10. instance_id_14059
Find the Keyword for which name is super-population viewpoint!

Gemma query:
```cypher
MATCH (k:Keyword {name: 'super-population viewpoint'}) RETURN k
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Equivalent Keyword label and exact name predicate; alias changes do not change meaning. No source graph was available, so this is a static judgement. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 11. instance_id_14512
Fetch the Keyword where key_id ends with d8!

Gemma query:
```cypher
MATCH (n:Keyword)
WHERE n.key_id ENDS WITH 'd8!'
RETURN n
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Reference regex d8.* tests a prefix rather than the requested suffix. Gemma uses ENDS WITH d8!, possibly treating sentence punctuation as literal data. Intended suffix punctuation is unresolved. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 12. instance_id_39698
Show the top 5 oldest movies in the collection with the highest revenue.

Gemma query:
```cypher
MATCH (m:Movie)-[:IN_COLLECTION]->(c:Collection)
WITH c, sum(m.revenue) AS total_revenue
ORDER BY total_revenue DESC
LIMIT 1
MATCH (movie:Movie)-[:IN_COLLECTION]->(c)
RETURN movie
ORDER BY movie.release_date ASC
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma selects the collection with greatest summed revenue and then its oldest movies. Reference never selects a highest-revenue collection. Revenue aggregation, ties and collection interpretation remain unresolved. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 13. instance_id_29243
Find the characters who have 'INTERACTS1' relationships with a 'weight' greater than 10.

Gemma query:
```cypher
MATCH (c:Character)-[r:INTERACTS1]->(:Character)
WHERE r.weight > 10
RETURN c
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Declared INTERACTS1/weight pattern is used. Gemma returns one Character node per edge rather than distinct reference names: 175 versus 53 rows. Unique-character and source-only interpretations require clarification. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 14. instance_id_27807
"Who is related to John Snow?"

Gemma query:
```cypher
MATCH (n:Character {name: 'John Snow'})-[:INTERACTS|INTERACTS1|INTERACTS2|INTERACTS3|INTERACTS45]-(related:Character) RETURN related.name
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: uncertain.

The generated undirected relationship-type union is equivalent to the reference pattern. Both return no rows; John Snow spelling/data coverage is unresolved. Static equivalence is not demonstrated answer correctness. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 15. instance_id_22532
Show the first 5 reviews with a star rating below 4.0.

Gemma query:
```cypher
MATCH (r:Review)
WHERE r.stars < 4.0
RETURN r
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

The low-star predicate is correct and Review nodes are an acceptable output. Gemma lacks reference date ordering and User/Business restrictions; the intended first-five ordering is unspecified. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 16. instance_id_5095
Fetch eight samples of the description of the Topic and the label for Topic!

Gemma query:
```cypher
MATCH (t:Topic) RETURN t.description, t.label LIMIT 8
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: issue_identified.

Gemma returns description and label from the same Topic, limited to eight. Reference independently matches two Topic variables and creates cross-pairs. Gemma is a reasonable direct interpretation of the requested samples. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 17. instance_id_10719
Find the nodes connected to Topic where cluster is 4 and list their properties!

Gemma query:
```cypher
MATCH (n)--(t:Topic {cluster: 4}) RETURN properties(n)
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: issue_identified.

Supplied schema declares Topic.cluster INTEGER: Gemma uses integer 4 and returns neighbour properties. Reference compares cluster with string 4. Undirected connectedness follows the question, although the sparse schema lacks endpoint evidence. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 18. instance_id_19058
Fetch the distinct values of the label from Topic where either description is Studies eigenvalues and eigenvectors of operators, analyzing how structures behave under various conditions in mathematics and physics. or label is not null!

Gemma query:
```cypher
MATCH (t:Topic)
WHERE t.description = 'Studies eigenvalues and eigenvectors of operators, analyzing how structures behave under various conditions in mathematics and physics.' OR t.label IS NOT NULL
RETURN DISTINCT t.label
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Equivalent OR predicate and DISTINCT Topic.label projection. The description text is preserved. Judgement is static because no source graph was available. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 19. instance_id_10822
Find all nodes directly connected to the Categories that has category_id 088fbf884bd7c6533956a45531b362b7!

Gemma query:
```cypher
MATCH (c:Categories {category_id: '088fbf884bd7c6533956a45531b362b7'})--(n) RETURN n
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: uncertain.

Gemma returns nodes directly connected in either direction to the selected Categories node. That fits the broad question wording; reference restricts outgoing paths and returns paths instead of nodes. Intended direction remains a reference concern. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 20. instance_id_39266
Find the first 5 businesses that have a category of 'Brewery'.

Gemma query:
```cypher
MATCH (b:Business)-[:IN_CATEGORY]->(c:Category {name: 'Brewery'})
RETURN b
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Same Brewery category pattern and limit five; Business nodes are an acceptable projection. Both queries omit ordering for first five, so a final ordered-selection judgement remains uncertain. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 21. instance_id_1170
What are the names of rooms that have either king or queen bed?

Gemma query:
```cypher
MATCH (n:Room) WHERE n.bedType = 'king' OR n.bedType = 'queen' RETURN n.roomName
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Room/bedType/roomName belong to the declared schema. Gemma uses lowercase king/queen whereas reference uses King/Queen; the schema provides no stored category values and the source graph is unavailable. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 22. instance_id_40923
Find all users who asked a question with the word 'error' in the text.

Gemma query:
```cypher
MATCH (u:User)-[:ASKED]->(q:Question)
WHERE q.text CONTAINS 'error'
RETURN u
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

ASKED direction and error substring agree. User-node projection is acceptable. Both can repeat users with multiple qualifying questions; distinct identities were not verified under the unique-user review rule. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 23. instance_id_32158
List the `companyName` of suppliers who supply products with a `reorderLevel` of 0.

Gemma query:
```cypher
MATCH (s:Supplier)-[:SUPPLIES]->(p:Product)
WHERE p.reorderLevel = 0
RETURN s.companyName
```

Syntax: no_error_identified; schema: no_error_identified; logical: error_present; reference: no_issue_identified.

Under the recorded unique-supplier-list rule, Gemma omits DISTINCT and returns 24 rows versus 18 reference names, including repeated supplier names in the saved preview. Relationship and filter agree. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 24. instance_id_28212
Which country has the highest number of entities that filed filings with an amount greater than 1000000?

Gemma query:
```cypher
MATCH (c:Country)<-[:COUNTRY]-(e:Entity)-[:FILED]->(f:Filing)
WHERE f.amount > 1000000
RETURN c.name
ORDER BY count(DISTINCT e) DESC
LIMIT 1
```

Syntax: error_present; schema: no_error_identified; logical: uncertain; reference: no_issue_identified.

Neo4j syntax validation rejected this query. COUNTRY/FILED endpoints and properties are declared, but ordering by an unprojected aggregate did not plan. Keep syntax failure separate from a semantic label. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 25. instance_id_25174
List all actors who have a poster URL that includes 'smile' in it.

Gemma query:
```cypher
MATCH (a:Actor) WHERE a.poster CONTAINS 'smile' RETURN a
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Generated query is textually identical to reference and directly implements the poster smile substring request. Both empty results are inconclusive database evidence, not proof of an error. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 26. instance_id_2654
How many people have worked as a project manager in London?

Gemma query:
```cypher
MATCH (p:Person)-[:HAS_POSITION]->(pos:Position)
WHERE pos.title = 'Project Manager' AND pos.location = 'London'
RETURN count(DISTINCT p)
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Gemma counts distinct people using exact case-sensitive job title/location; reference uses case-insensitive substrings and counts matches. Broader position names, locality values and duplicate people remain unchecked. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 27. instance_id_25306
Which movies have a director who was born after 1960 and have generated over 100 million in revenue?

Gemma query:
```cypher
MATCH (d:Director)-[:DIRECTED]->(m:Movie)
WHERE d.born.year > 1960 AND m.revenue > 100000000
RETURN m.title
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Declared Director.born and Movie.revenue are used. Gemma excludes the entire year 1960; reference includes dates after January 1, 1960. After 1960 is ambiguous; titles are acceptable but duplicate movie matches are unchecked. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 28. instance_id_33128
List the summaries of reviews for movies with a rating lower than 60.

Gemma query:
```cypher
MATCH (:Person)-[r:REVIEWED]->(:Movie)
WHERE r.rating < 60
RETURN r.summary
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Same REVIEWED relationship, rating-below-60 filter and relationship summary projection. Saved execution results match. This supports the inspected question interpretation without establishing independent ground truth. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 29. instance_id_32549
What is the average freight of orders made by the customer with customerID equal to 'ERNSH'?

Gemma query:
```cypher
MATCH (:Customer {customerID: 'ERNSH'})-[:PURCHASED]->(o:Order) RETURN avg(o.freight)
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: no_issue_identified.

Declared Order.freight property is used, but saved execution fails because AVG receives String without toFloat. Reference converts the value. Record execution/type error separately; the logical filter and intended aggregation are otherwise aligned. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 30. instance_id_34335
List the first 5 movies released in 1995.

Gemma query:
```cypher
MATCH (m:Movie)
WHERE m.release_date.year = 1995
RETURN m.title
ORDER BY m.release_date ASC
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Same release-year predicate, chronological ascending order and five-title limit. Saved results match. Equal-date tie policy is unspecified in both. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 31. instance_id_467
What are the different majors?

Gemma query:
```cypher
MATCH (s:Student) RETURN DISTINCT s.Major
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Generated query equals reference: DISTINCT Student.Major implements different majors using a declared property. No source graph was available. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 32. instance_id_25423
Retrieve the top 3 highest viewed questions that have been answered by users with less than 3 answers in total.

Gemma query:
```cypher
MATCH (u:User)-[:PROVIDED]->(a:Answer)
WITH u, count(a) AS answer_count
WHERE answer_count < 3
MATCH (u)-[:PROVIDED]->(:Answer)-[:ANSWERED]->(q:Question)
RETURN DISTINCT q
ORDER BY q.view_count DESC
LIMIT 3
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma counts total answers per user before finding answered questions; reference groups by user and question, contradicting total answers. Generated null/tie ordering among most-viewed questions remains unchecked. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 33. instance_id_15256
Find the Journal where journal_id is 99571eecaa5c5d622bb0d1f855752d5f!

Gemma query:
```cypher
MATCH (n:Journal {journal_id: '99571eecaa5c5d622bb0d1f855752d5f'}) RETURN n
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Declared Journal.journal_id equality is equivalent to the reference WHERE predicate; returning the Journal node fits the request. No source graph available. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 34. instance_id_15868
Find eight instances of Article where either article_id exceeds 1010 or article_id is less than 1048!

Gemma query:
```cypher
MATCH (a:Article)
WHERE a.article_id > 1010 OR a.article_id < 1048
LIMIT 8
RETURN a
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Saved Neo4j accepted LIMIT before RETURN. The declared integer article_id OR predicate and eight-node limit are preserved. OR covers all non-null integer values here, as in the question/reference; source execution was unavailable. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 35. instance_id_41904
Who are the CEOs of the first 3 public companies?

Gemma query:
```cypher
MATCH (o:Organization)-[:HAS_CEO]->(p:Person) WHERE o.isPublic = true RETURN p.name LIMIT 3
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Gemma uses the declared Organization-to-Person HAS_CEO direction and public-company flag. It returns names but does not impose reference alphabetical order. First three is undefined in the question. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 36. instance_id_40421
List the first 5 organizations that have a CEO with a summary mentioning 'Leader'.

Gemma query:
```cypher
MATCH (o:Organization)-[:HAS_CEO]->(p:Person)
WHERE p.summary CONTAINS 'Leader'
RETURN o
LIMIT 5
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: uncertain.

Same HAS_CEO pattern, Leader summary substring and limit five; organisation-node projection is acceptable. First ordering and unique organisation treatment remain unspecified; no final ordered-selection claim. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 37. instance_id_30995
What is the sourceID of the entity with internal_id '1001256'?

Gemma query:
```cypher
MATCH (e:Entity {internal_id: '1001256'})
RETURN e.sourceID
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Same Entity.internal_id equality and sourceID projection. Properties belong to Entity and saved results match. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 38. instance_id_1947
What are the names of all songs in English?

Gemma query:
```cypher
MATCH (s:Song) WHERE s.languages = 'English' RETURN s.song_name
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma uses declared Song.song_name, while reference uses undeclared Song.Song_name. Generated English versus reference english literal can alter matching; actual stored values are unavailable. The genre restriction in reference is also not requested. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 39. instance_id_29249
Find the characters who interacted with 'Aemon-Targaryen-(Dragonknight)' in 'INTERACTS3' relationship.

Gemma query:
```cypher
MATCH (c:Character {name: 'Aemon-Targaryen-(Dragonknight)'})-[:INTERACTS3]-(other:Character)
RETURN other.name
```

Syntax: no_error_identified; schema: no_error_identified; logical: no_error_identified; reference: no_issue_identified.

Same named Character, undirected INTERACTS3 connection and neighbour-name projection. Saved results match. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.

## 40. instance_id_7850
Find the Journal with a journal_id starting with J, and linked with an Article through PUBLISHED_IN relationship. The Article must have title: Classification of Subsystems for Local Nets with Trivial Superselection
  Structure and be PUBLISHED_IN with meta recorded!

Gemma query:
```cypher
MATCH (a:Article)-[r:PUBLISHED_IN]->(j:Journal)
WHERE j.journal_id STARTS WITH 'J' 
  AND a.title = 'Classification of Subsystems for Local Nets with Trivial Superselection Structure' 
  AND r.meta IS NOT NULL
RETURN j
```

Syntax: no_error_identified; schema: no_error_identified; logical: uncertain; reference: issue_identified.

Gemma follows declared Article-to-Journal PUBLISHED_IN direction, checks relationship meta and returns Journal. Reference returns undeclared Article.journal_id. Exact title whitespace differs between question/reference/Gemma, leaving literal matching unresolved. Schema judgement covers inspected declared names, property ownership and explicit typed patterns; untyped relationships in sparse schemas cannot be fully validated.
