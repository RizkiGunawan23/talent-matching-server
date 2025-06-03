import datetime
import uuid

from neo4j import Driver, Session, Transaction


class SafeNeo4jBackupRestore:
    """Safe dynamic backup and restore system that handles missing data gracefully"""

    def __init__(self, driver: Driver):
        self.driver = driver

    def check_label_exists(self, label: str, session: Session) -> bool:
        """Check if a label exists in the database"""
        try:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) AS count LIMIT 1")
            count = list(result)[0]["count"]
            return count > 0
        except Exception:
            return False

    def check_relationship_exists(self, rel_type: str, session: Session) -> bool:
        """Check if a relationship type exists in the database"""
        try:
            result = session.run(
                f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count LIMIT 1"
            )
            count = list(result)[0]["count"]
            return count > 0
        except Exception:
            return False

    def get_existing_labels(self, session: Session) -> list[str]:
        """Get all existing labels in the database"""
        try:
            result = session.run("CALL db.labels() YIELD label RETURN label")
            return [record["label"] for record in result]
        except Exception:
            return []

    def get_existing_relationship_types(self, session: Session) -> list[str]:
        """Get all existing relationship types in the database"""
        try:
            result = session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            return [record["relationshipType"] for record in result]
        except Exception:
            return []

    def safe_backup_nodes_by_labels(self, labels: list[str]) -> dict[str, any]:
        """Safely backup nodes by their labels, skipping non-existent ones"""
        backup_data = {}

        with self.driver.session() as session:
            existing_labels = self.get_existing_labels(session)

            for label in labels:
                if label not in existing_labels:
                    print(f"   ⚠️ Skipping {label} - label not found in database")
                    backup_data[f"{label.lower()}_nodes"] = []
                    continue

                try:
                    print(f"   📦 Backing up {label} nodes...")

                    query = f"""
                    MATCH (n:{label})
                    RETURN properties(n) AS props,
                        id(n) AS node_id,
                        labels(n) AS labels
                    ORDER BY id(n)
                    """

                    result = session.run(query)
                    nodes = []

                    for record in result:
                        nodes.append(
                            {
                                "node_id": record["node_id"],
                                "properties": record["props"],
                                "labels": record["labels"],
                            }
                        )

                    backup_data[f"{label.lower()}_nodes"] = nodes
                    print(f"     ✅ Backed up {len(nodes)} {label} nodes")

                except Exception as e:
                    print(f"     ⚠️ Error backing up {label}: {e}")
                    backup_data[f"{label.lower()}_nodes"] = []

        return backup_data

    def safe_backup_relationships_by_types(
        self, relationship_types: list[str]
    ) -> dict[str, any]:
        """Safely backup relationships by their types, skipping non-existent ones"""
        backup_data = {}

        with self.driver.session() as session:
            existing_rel_types = self.get_existing_relationship_types(session)

            for rel_type in relationship_types:
                if rel_type not in existing_rel_types:
                    print(
                        f"   ⚠️ Skipping {rel_type} - relationship type not found in database"
                    )
                    backup_data[f"{rel_type.lower()}_relationships"] = []
                    continue

                try:
                    print(f"   🔗 Backing up {rel_type} relationships...")

                    query = f"""
                    MATCH (start)-[r:{rel_type}]->(end)
                    RETURN startNode(r) AS start_node,
                        endNode(r) AS end_node,
                        properties(r) AS rel_props,
                        type(r) AS rel_type,
                        labels(startNode(r)) AS start_labels,
                        labels(endNode(r)) AS end_labels,
                        properties(startNode(r)) AS start_props,
                        properties(endNode(r)) AS end_props
                    """

                    result = session.run(query)
                    relationships = []

                    for record in result:
                        relationships.append(
                            {
                                "start_node_labels": record["start_labels"],
                                "start_node_props": record["start_props"],
                                "end_node_labels": record["end_labels"],
                                "end_node_props": record["end_props"],
                                "relationship_type": record["rel_type"],
                                "relationship_props": record["rel_props"],
                            }
                        )

                    backup_data[f"{rel_type.lower()}_relationships"] = relationships
                    print(
                        f"     ✅ Backed up {len(relationships)} {rel_type} relationships"
                    )

                except Exception as e:
                    print(f"     ⚠️ Error backing up {rel_type} relationships: {e}")
                    backup_data[f"{rel_type.lower()}_relationships"] = []

        return backup_data

    def safe_backup_node_relationships(
        self,
        node_label: str,
        relationship_types: list[str],
        node_identifier: str = "id",
    ) -> dict[str, any]:
        """Safely backup specific node with its relationships"""
        backup_data = {}

        with self.driver.session() as session:
            # Check if node label exists
            if not self.check_label_exists(node_label, session):
                print(f"   ⚠️ Skipping {node_label} - label not found in database")
                backup_data[f"{node_label.lower()}_with_relationships"] = []
                return backup_data

            # Filter existing relationship types
            existing_rel_types = self.get_existing_relationship_types(session)
            valid_rel_types = [
                rt for rt in relationship_types if rt in existing_rel_types
            ]

            if not valid_rel_types:
                print(f"   ⚠️ No valid relationship types found for {node_label}")
                backup_data[f"{node_label.lower()}_with_relationships"] = []
                return backup_data

            try:
                print(f"   🎯 Backing up {node_label} nodes with relationships...")
                print(f"     Valid relationships: {valid_rel_types}")

                # Build relationship patterns for existing types only
                rel_patterns = []
                return_clauses = []

                for i, rel_type in enumerate(valid_rel_types):
                    rel_patterns.append(
                        f"OPTIONAL MATCH (n)-[r{i}:{rel_type}]-(related{i})"
                    )
                    return_clauses.extend(
                        [
                            f"collect(DISTINCT {{type: type(r{i}), props: properties(r{i}), "
                            f"related_labels: labels(related{i}), related_props: properties(related{i})}}) AS {rel_type.lower()}_rels"
                        ]
                    )

                query = f"""
                MATCH (n:{node_label})
                {' '.join(rel_patterns)}
                RETURN n,
                    properties(n) AS node_props,
                    labels(n) AS node_labels,
                    id(n) AS node_id,
                    {', '.join(return_clauses)}
                ORDER BY id(n)
                """

                result = session.run(query)
                nodes_with_rels = []

                for record in result:
                    node_data = {
                        "node_id": record["node_id"],
                        "properties": record["node_props"],
                        "labels": record["node_labels"],
                        "relationships": {},
                    }

                    # Add relationships
                    for rel_type in valid_rel_types:
                        rel_key = f"{rel_type.lower()}_rels"
                        if rel_key in record:
                            # Filter out empty relationships
                            valid_rels = [
                                rel
                                for rel in record[rel_key]
                                if rel["type"] is not None
                            ]
                            node_data["relationships"][rel_type] = valid_rels

                    nodes_with_rels.append(node_data)

                backup_data[f"{node_label.lower()}_with_relationships"] = (
                    nodes_with_rels
                )
                print(
                    f"     ✅ Backed up {len(nodes_with_rels)} {node_label} nodes with relationships"
                )

            except Exception as e:
                print(f"     ⚠️ Error backing up {node_label} with relationships: {e}")
                backup_data[f"{node_label.lower()}_with_relationships"] = []

        return backup_data

    def safe_full_dynamic_backup(self, config: dict[str, any]) -> dict[str, any]:
        """Perform full safe backup based on configuration"""
        backup_data = {
            "metadata": {
                "backup_timestamp": datetime.datetime.now().isoformat(),
                "config": config,
                "warnings": [],
            }
        }

        warnings = []

        # Safe backup individual nodes
        if "node_labels" in config and config["node_labels"]:
            try:
                node_backup = self.safe_backup_nodes_by_labels(config["node_labels"])
                backup_data.update(node_backup)
            except Exception as e:
                warning = f"Error backing up node labels: {e}"
                warnings.append(warning)
                print(f"   ⚠️ {warning}")

        # Safe backup individual relationships
        if "relationship_types" in config and config["relationship_types"]:
            try:
                rel_backup = self.safe_backup_relationships_by_types(
                    config["relationship_types"]
                )
                backup_data.update(rel_backup)
            except Exception as e:
                warning = f"Error backing up relationship types: {e}"
                warnings.append(warning)
                print(f"   ⚠️ {warning}")

        # Safe backup nodes with their relationships
        if "nodes_with_relationships" in config and config["nodes_with_relationships"]:
            for node_config in config["nodes_with_relationships"]:
                try:
                    node_label = node_config["label"]
                    rel_types = node_config["relationships"]
                    identifier = node_config.get("identifier", "id")

                    node_rel_backup = self.safe_backup_node_relationships(
                        node_label, rel_types, identifier
                    )
                    backup_data.update(node_rel_backup)
                except Exception as e:
                    warning = f"Error backing up {node_config.get('label', 'unknown')} with relationships: {e}"
                    warnings.append(warning)
                    print(f"   ⚠️ {warning}")

        # Calculate totals
        total_items = 0
        for key, value in backup_data.items():
            if isinstance(value, list):
                total_items += len(value)

        backup_data["metadata"]["total_items"] = total_items
        backup_data["metadata"]["warnings"] = warnings

        print(f"\n   ✅ Safe dynamic backup completed: {total_items} items")
        if warnings:
            print(f"   ⚠️ {len(warnings)} warnings occurred")

        return backup_data

    def safe_restore_nodes(self, backup_data: dict[str, any], tx: Transaction) -> int:
        """Safely restore nodes from backup data using MERGE to avoid duplicates"""
        total_restored = 0

        for key, nodes in backup_data.items():
            if key.endswith("_nodes") and isinstance(nodes, list):
                if not nodes:  # Skip empty collections
                    continue

                label = key.replace("_nodes", "").replace("_", "").title()

                try:
                    print(f"   📦 Restoring {label} nodes...")

                    restored = 0
                    for node in nodes:
                        try:
                            props = node["properties"]
                            labels = node["labels"]

                            # Get unique property for MERGE
                            unique_prop = self._get_unique_property(props)
                            if not unique_prop:
                                print(
                                    f"     ⚠️ No unique property found for {label} node, skipping..."
                                )
                                continue

                            # Build labels string
                            labels_str = ":".join(labels)

                            # Use MERGE instead of CREATE to avoid duplicates
                            query = f"""
                            MERGE (n:{labels_str} {{{unique_prop[0]}: $unique_value}})
                            SET n = $props
                            """

                            tx.run(query, unique_value=unique_prop[1], props=props)
                            restored += 1

                        except Exception as e:
                            print(
                                f"     ⚠️ Error restoring individual {label} node: {e}"
                            )
                            continue

                    print(f"     ✅ Restored {restored} {label} nodes (using MERGE)")
                    total_restored += restored

                except Exception as e:
                    print(f"     ⚠️ Error restoring {label} nodes: {e}")
                    continue

        return total_restored

    def safe_restore_relationships(
        self, backup_data: dict[str, any], tx: Transaction
    ) -> int:
        """Safely restore relationships from backup data using MERGE to avoid duplicates"""
        total_restored = 0

        for key, relationships in backup_data.items():
            if key.endswith("_relationships") and isinstance(relationships, list):
                if not relationships:  # Skip empty collections
                    continue

                rel_type = key.replace("_relationships", "").upper()

                try:
                    print(f"   🔗 Restoring {rel_type} relationships...")

                    restored = 0
                    for rel in relationships:
                        try:
                            start_labels = rel["start_node_labels"]
                            start_props = rel["start_node_props"]
                            end_labels = rel["end_node_labels"]
                            end_props = rel["end_node_props"]
                            rel_props = rel["relationship_props"]

                            # Build match patterns
                            start_labels_str = ":".join(start_labels)
                            end_labels_str = ":".join(end_labels)

                            # Find unique property for matching
                            start_match_prop = self._get_unique_property(start_props)
                            end_match_prop = self._get_unique_property(end_props)

                            if start_match_prop and end_match_prop:
                                # Use MERGE for both nodes and relationship to avoid duplicates
                                query = f"""
                                MERGE (start:{start_labels_str} {{{start_match_prop[0]}: $start_value}})
                                SET start = $start_props
                                MERGE (end:{end_labels_str} {{{end_match_prop[0]}: $end_value}})
                                SET end = $end_props
                                MERGE (start)-[r:{rel_type}]->(end)
                                SET r = $rel_props
                                """

                                tx.run(
                                    query,
                                    start_value=start_match_prop[1],
                                    end_value=end_match_prop[1],
                                    start_props=start_props,
                                    end_props=end_props,
                                    rel_props=rel_props,
                                )
                                restored += 1
                        except Exception as e:
                            print(
                                f"     ⚠️ Error restoring individual {rel_type} relationship: {e}"
                            )
                            continue

                    print(
                        f"     ✅ Restored {restored} {rel_type} relationships (using MERGE)"
                    )
                    total_restored += restored

                except Exception as e:
                    print(f"     ⚠️ Error restoring {rel_type} relationships: {e}")
                    continue

        return total_restored

    def safe_restore_nodes_with_relationships(
        self, backup_data: dict[str, any], tx: Transaction
    ) -> int:
        """Restore nodes with their relationships using MERGE to avoid duplicates"""
        total_restored = 0

        for key, nodes_with_rels in backup_data.items():
            if key.endswith("_with_relationships") and isinstance(
                nodes_with_rels, list
            ):
                if not nodes_with_rels:  # Skip empty collections
                    continue

                label = key.replace("_with_relationships", "").title()
                print(f"   🎯 Restoring {label} with relationships...")

                restored = 0
                for node_data in nodes_with_rels:
                    try:
                        # Restore node first using MERGE
                        props = node_data["properties"]
                        labels = node_data["labels"]
                        relationships = node_data["relationships"]

                        # Get unique property for main node
                        node_match_prop = self._get_unique_property(props)
                        if not node_match_prop:
                            print(
                                f"     ⚠️ No unique property found for {label} node, skipping..."
                            )
                            continue

                        labels_str = ":".join(labels)

                        # Use MERGE for main node
                        merge_node_query = f"""
                        MERGE (n:{labels_str} {{{node_match_prop[0]}: $node_value}})
                        SET n = $props
                        """

                        tx.run(
                            merge_node_query, node_value=node_match_prop[1], props=props
                        )

                        # Restore relationships
                        rel_count = 0
                        for rel_type, rels in relationships.items():
                            for rel in rels:
                                if rel.get("type"):  # Skip empty relationships
                                    related_labels = rel.get("related_labels", [])
                                    related_props = rel.get("related_props", {})
                                    rel_props = rel.get("props", {})

                                    if related_labels and related_props:
                                        related_labels_str = ":".join(related_labels)
                                        match_prop = self._get_unique_property(
                                            related_props
                                        )

                                        if match_prop and node_match_prop:
                                            # Use MERGE for everything to avoid duplicates
                                            query = f"""
                                            MERGE (n:{labels_str} {{{node_match_prop[0]}: $node_value}})
                                            MERGE (related:{related_labels_str} {{{match_prop[0]}: $related_value}})
                                            SET related = $related_props
                                            MERGE (n)-[r:{rel_type}]->(related)
                                            SET r = $rel_props
                                            """

                                            tx.run(
                                                query,
                                                node_value=node_match_prop[1],
                                                related_value=match_prop[1],
                                                related_props=related_props,
                                                rel_props=rel_props,
                                            )
                                            rel_count += 1

                        print(
                            f"     📎 Restored {rel_count} relationships for {label} node (using MERGE)"
                        )
                        restored += 1

                    except Exception as e:
                        print(f"     ⚠️ Error restoring {label} node: {e}")
                        continue

                print(
                    f"     ✅ Restored {restored} {label} with relationships (using MERGE)"
                )
                total_restored += restored

        return total_restored

    def enrich_user_nodes_from_data(self, users_data: list, tx: Transaction) -> int:
        """Enrich User nodes with additional properties from users_data variable"""
        print("👤 Enriching User nodes with additional properties...")

        try:
            users_list = users_data
            print(f"   Found {len(users_list)} users in data")

            updated_count = 0
            for user in users_list:
                try:
                    # Find user by email and update properties
                    email = user.get("email")
                    if not email:
                        continue

                    # Prepare additional properties
                    additional_props = {
                        "name": user.get("name"),
                        "profile_image": user.get("profile_image"),
                        "password": user.get("password"),
                        "uuid": user.get(
                            "uuid", str(uuid.uuid4())
                        ),  # Generate if not exists
                    }

                    # Remove None values
                    additional_props = {
                        k: v for k, v in additional_props.items() if v is not None
                    }

                    # Update user node
                    query = """
                    MATCH (u:User {email: $email})
                    SET u += $additional_props
                    RETURN count(u) AS updated
                    """

                    result = tx.run(
                        query, email=email, additional_props=additional_props
                    )
                    updated = list(result)[0]["updated"]

                    if updated > 0:
                        updated_count += 1
                        print(f"     ✅ Updated User: {email}")
                    else:
                        print(f"     ⚠️ User not found: {email}")

                except Exception as e:
                    print(
                        f"     ❌ Error updating user {user.get('email', 'unknown')}: {e}"
                    )
                    continue

            print(f"   ✅ Successfully enriched {updated_count} User nodes")
            return updated_count

        except Exception as e:
            print(f"   ❌ Error enriching User nodes: {e}")
            return 0

    def enrich_job_nodes_from_data(self, jobs_data: list, tx: Transaction) -> int:
        """Enrich Job nodes with additional properties from jobs_data variable"""
        print("💼 Enriching Job nodes with additional properties...")

        try:
            jobs_list = jobs_data
            print(f"   Found {len(jobs_list)} jobs in data")

            updated_count = 0
            for job in jobs_list:
                try:
                    # Find job by job_url and update properties
                    job_url = job.get("job_url")
                    if not job_url:
                        continue

                    # Prepare additional properties
                    additional_props = {
                        "imageUrl": job.get("image_url"),
                        "jobTitle": job.get("job_title"),
                        "companyName": job.get("company_name"),
                        "subdistrict": job.get("subdistrict"),
                        "city": job.get("city"),
                        "province": job.get("province"),
                        "minimumSalary": job.get("minimum_salary"),
                        "maximumSalary": job.get("maximum_salary"),
                        "employmentType": job.get("employment_type"),
                        "workSetup": job.get("work_setup"),
                        "minimumEducation": job.get("minimum_education"),
                        "minimumExperience": job.get("minimum_experience"),
                        "maximumExperience": job.get("maximum_experience"),
                        "jobDescription": job.get("job_description"),
                        "scrapedAt": job.get("scraped_at"),
                    }

                    # Remove None values
                    additional_props = {
                        k: v for k, v in additional_props.items() if v is not None
                    }

                    # Update job node
                    query = """
                    MATCH (j:Job {jobUrl: $job_url})
                    SET j += $additional_props
                    RETURN count(j) AS updated
                    """

                    result = tx.run(
                        query, job_url=job_url, additional_props=additional_props
                    )
                    updated = list(result)[0]["updated"]

                    if updated > 0:
                        updated_count += 1
                        if updated_count % 100 == 0:
                            print(f"     ✅ Updated {updated_count} jobs...")

                except Exception as e:
                    print(
                        f"     ❌ Error updating job {job.get('job_url', 'unknown')}: {e}"
                    )
                    continue

            print(f"   ✅ Successfully enriched {updated_count} Job nodes")
            return updated_count

        except Exception as e:
            print(f"   ❌ Error enriching Job nodes: {e}")
            return 0

    def enrich_nodes_with_data(
        self,
        tx: Transaction,
        users_data: list[dict] | None = [],
        jobs_data: list[dict] | None = [],
    ) -> dict:
        """Enrich nodes with additional properties from data variables"""
        print("🔄 Starting node enrichment process...")

        enrichment_stats = {"users_updated": 0, "jobs_updated": 0}

        # Enrich User nodes
        if users_data:
            try:
                users_updated = self.enrich_user_nodes_from_data(users_data, tx)
                enrichment_stats["users_updated"] = users_updated
            except Exception as e:
                print(f"   ❌ Failed to enrich User nodes: {e}")

        # Enrich Job nodes
        if jobs_data:
            try:
                jobs_updated = self.enrich_job_nodes_from_data(jobs_data, tx)
                enrichment_stats["jobs_updated"] = jobs_updated
            except Exception as e:
                print(f"   ❌ Failed to enrich Job nodes: {e}")

        total_updated = (
            enrichment_stats["users_updated"] + enrichment_stats["jobs_updated"]
        )
        print(f"✅ Node enrichment completed: {total_updated} nodes updated")

        return enrichment_stats

    def safe_full_dynamic_restore_with_enrichment(
        self,
        backup_data: dict[str, any],
        tx: Transaction,
        users_data: list[dict] | None = [],
        jobs_data: list[dict] | None = [],
    ) -> bool:
        """Safely perform full restore from backup data with node enrichment from variables"""
        if not backup_data or "metadata" not in backup_data:
            print("   ⚠️ No valid backup data to restore")
            return False

        print(
            f"   🔄 Safely restoring data from {backup_data['metadata']['backup_timestamp']}"
        )

        total_restored = 0

        try:
            # Step 1: Restore nodes first
            total_restored += self.safe_restore_nodes(backup_data, tx)

            # Step 2: Restore standalone relationships
            total_restored += self.safe_restore_relationships(backup_data, tx)

            # Step 3: Restore nodes with their relationships
            total_restored += self.safe_restore_nodes_with_relationships(
                backup_data, tx
            )

            print(
                f"   ✅ Safe dynamic restore completed: {total_restored} items restored"
            )

            # Step 4: Enrich nodes with additional properties from data variables
            if users_data or jobs_data:
                print("   🎯 Starting node enrichment...")
                enrichment_stats = self.enrich_nodes_with_data(
                    tx, users_data, jobs_data
                )

                print(f"   📊 Enrichment Summary:")
                print(f"     Users enriched: {enrichment_stats['users_updated']}")
                print(f"     Jobs enriched: {enrichment_stats['jobs_updated']}")

            # Show warnings if any
            if (
                "warnings" in backup_data["metadata"]
                and backup_data["metadata"]["warnings"]
            ):
                print(
                    f"   ⚠️ Backup had {len(backup_data['metadata']['warnings'])} warnings"
                )

            return True

        except Exception as e:
            print(f"   ❌ Error during safe restore with enrichment: {e}")
            return False

    def _get_unique_property(self, props: dict[str, any]) -> tuple | None:
        """Get a unique property for matching nodes"""
        # Priority order for unique properties
        unique_props = ["email", "uid", "jobUrl", "name", "id"]

        for prop in unique_props:
            if prop in props and props[prop] is not None:
                return (prop, props[prop])

        # If no standard unique property, use first available property
        for key, value in props.items():
            if value is not None:
                return (key, value)

        return None
