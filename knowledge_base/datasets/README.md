# Provenance and Dataset Documentation

## Public Defect Datasets
This knowledge base is seeded with representative historical defect records from public archives:
1. **Mozilla Bugzilla:** Firefox and SpiderMonkey defect reports with C++ and JavaScript stack traces.
2. **Apache Jira:** Apache Commons, HTTPD, and Kafka issues covering Java exceptions and concurrency faults.
3. **Eclipse Bugzilla:** Eclipse Platform and JDT compiler defects focusing on classpath and JVM errors.

## Data Usage and Schema
Raw records are processed through adapters in `knowledge_base/adapters/`, cleaned of HTML and authentication tokens by `DataCleaner`, and chunked into `title_description`, `stack_trace`, `comment`, and `resolution` segments before vector indexing in ChromaDB.
