select ?p ?o
where {
	<2319117314> <rdf:type> <foaf:Person> .
	<2319117314> ?p ?o . 
	FILTER ( ?p!=<foaf:knows> )
}