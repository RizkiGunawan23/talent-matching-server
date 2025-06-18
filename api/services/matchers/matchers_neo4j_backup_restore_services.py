import datetime
import uuid

from neomodel import db

from api.models import Job, Maintenance, MatchingTask, ScrapingTask, User


def check_label_exists(label: str) -> bool:
    """Check if a label exists in the database using ORM"""
    try:
        result, _ = db.cypher_query(
            f"MATCH (n:{label}) RETURN count(n) AS count LIMIT 1"
        )
        count = result[0][0] if result else 0
        return count > 0
    except Exception:
        return False


def check_relationship_exists(rel_type: str) -> bool:
    """Check if a relationship type exists in the database using ORM"""
    try:
        result, _ = db.cypher_query(
            f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count LIMIT 1"
        )
        count = result[0][0] if result else 0
        return count > 0
    except Exception:
        return False


def get_existing_labels() -> list[str]:
    """Get all existing labels in the database using ORM"""
    try:
        result, _ = db.cypher_query("CALL db.labels() YIELD label RETURN label")
        return [record[0] for record in result]
    except Exception:
        return []


def get_existing_relationship_types() -> list[str]:
    """Get all existing relationship types in the database using ORM"""
    try:
        result, _ = db.cypher_query(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )
        return [record[0] for record in result]
    except Exception:
        return []


def backup_nodes_by_labels(labels: list[str]) -> dict[str, any]:
    """Backup nodes by their labels using ORM, skipping non-existent ones"""
    backup_data = {}
    existing_labels = get_existing_labels()

    for label in labels:
        if label not in existing_labels:
            print(f"   ⚠️ Skipping {label} - label not found in database")
            backup_data[f"{label.lower()}_nodes"] = []
            continue

        try:
            print(f"   📦 Backing up {label} nodes...")

            # Use ORM for known models, fallback to cypher for others
            nodes = []
            if label == "User":
                users = User.nodes.all()
                for user in users:
                    nodes.append(
                        {
                            "node_id": (
                                user.element_id if hasattr(user, "element_id") else None
                            ),
                            "properties": {
                                "uid": user.uid,
                                "name": user.name,
                                "email": user.email,
                                "password": user.password,
                                "profilePicture": user.profilePicture,
                                "role": user.role,
                            },
                            "labels": ["User"],
                        }
                    )
            elif label == "ScrapingTask":
                tasks = ScrapingTask.nodes.all()
                for task in tasks:
                    nodes.append(
                        {
                            "node_id": (
                                task.element_id if hasattr(task, "element_id") else None
                            ),
                            "properties": {
                                "uid": task.uid,
                                "status": task.status,
                                "startedAt": task.startedAt,
                                "finishedAt": task.finishedAt,
                                "message": task.message,
                            },
                            "labels": ["ScrapingTask"],
                        }
                    )
            elif label == "MatchingTask":
                tasks = MatchingTask.nodes.all()
                for task in tasks:
                    nodes.append(
                        {
                            "node_id": (
                                task.element_id if hasattr(task, "element_id") else None
                            ),
                            "properties": {
                                "uid": task.uid,
                                "status": task.status,
                                "startedAt": task.startedAt,
                                "finishedAt": task.finishedAt,
                            },
                            "labels": ["MatchingTask"],
                        }
                    )
            elif label == "Maintenance":
                maintenance = Maintenance.nodes.all()
                for m in maintenance:
                    nodes.append(
                        {
                            "node_id": (
                                m.element_id if hasattr(m, "element_id") else None
                            ),
                            "properties": {
                                "isMaintenance": m.isMaintenance,
                            },
                            "labels": ["Maintenance"],
                        }
                    )
            else:
                # Fallback to cypher for unknown labels
                query = f"""
                MATCH (n:{label})
                RETURN properties(n) AS props,
                    id(n) AS node_id,
                    labels(n) AS labels
                ORDER BY id(n)
                """
                result, _ = db.cypher_query(query)
                for record in result:
                    nodes.append(
                        {
                            "node_id": record[1],
                            "properties": record[0],
                            "labels": record[2],
                        }
                    )

            backup_data[f"{label.lower()}_nodes"] = nodes
            print(f"     ✅ Backed up {len(nodes)} {label} nodes")

        except Exception as e:
            print(f"     ⚠️ Error backing up {label}: {e}")
            backup_data[f"{label.lower()}_nodes"] = []

    return backup_data


def backup_relationships_by_types(relationship_types: list[str]) -> dict[str, any]:
    """Backup relationships by their types using ORM, skipping non-existent ones"""
    backup_data = {}
    existing_rel_types = get_existing_relationship_types()

    for rel_type in relationship_types:
        if rel_type not in existing_rel_types:
            print(f"   ⚠️ Skipping {rel_type} - relationship type not found in database")
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

            result, _ = db.cypher_query(query)
            relationships = []

            for record in result:
                relationships.append(
                    {
                        "start_node_labels": record[4],
                        "start_node_props": record[6],
                        "end_node_labels": record[5],
                        "end_node_props": record[7],
                        "relationship_type": record[3],
                        "relationship_props": record[2],
                    }
                )

            backup_data[f"{rel_type.lower()}_relationships"] = relationships
            print(f"     ✅ Backed up {len(relationships)} {rel_type} relationships")

        except Exception as e:
            print(f"     ⚠️ Error backing up {rel_type} relationships: {e}")
            backup_data[f"{rel_type.lower()}_relationships"] = []

    return backup_data


def backup_node_relationships(
    node_label: str,
    relationship_types: list[str],
) -> dict[str, any]:
    """Backup specific node with its relationships using ORM where possible"""
    backup_data = {}

    # Check if node label exists
    if not check_label_exists(node_label):
        print(f"   ⚠️ Skipping {node_label} - label not found in database")
        backup_data[f"{node_label.lower()}_with_relationships"] = []
        return backup_data

    # Filter existing relationship types
    existing_rel_types = get_existing_relationship_types()
    valid_rel_types = [rt for rt in relationship_types if rt in existing_rel_types]

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
            rel_patterns.append(f"OPTIONAL MATCH (n)-[r{i}:{rel_type}]-(related{i})")
            return_clauses.append(
                f"collect(DISTINCT {{type: type(r{i}), props: properties(r{i}), "
                f"related_labels: labels(related{i}), related_props: properties(related{i})}}) AS {rel_type.lower()}_rels"
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

        result, _ = db.cypher_query(query)
        nodes_with_rels = []

        for record in result:
            node_data = {
                "node_id": record[3],
                "properties": record[1],
                "labels": record[2],
                "relationships": {},
            }

            # Add relationships
            for i, rel_type in enumerate(valid_rel_types):
                rel_key_index = 4 + i  # Start from index 4
                if len(record) > rel_key_index:
                    # Filter out empty relationships
                    valid_rels = [
                        rel
                        for rel in record[rel_key_index]
                        if rel.get("type") is not None
                    ]
                    node_data["relationships"][rel_type] = valid_rels

            nodes_with_rels.append(node_data)

        backup_data[f"{node_label.lower()}_with_relationships"] = nodes_with_rels
        print(
            f"     ✅ Backed up {len(nodes_with_rels)} {node_label} nodes with relationships"
        )

    except Exception as e:
        print(f"     ⚠️ Error backing up {node_label} with relationships: {e}")
        backup_data[f"{node_label.lower()}_with_relationships"] = []

    return backup_data


def perform_full_dynamic_backup(config: dict[str, any]) -> dict[str, any]:
    """Perform full backup based on configuration using ORM where possible"""
    backup_data = {
        "metadata": {
            "backup_timestamp": datetime.datetime.now().isoformat(),
            "config": config,
            "warnings": [],
        }
    }

    warnings = []

    # Backup individual nodes
    if "node_labels" in config and config["node_labels"]:
        try:
            node_backup = backup_nodes_by_labels(config["node_labels"])
            backup_data.update(node_backup)
        except Exception as e:
            warning = f"Error backing up node labels: {e}"
            warnings.append(warning)
            print(f"   ⚠️ {warning}")

    # Backup individual relationships
    if "relationship_types" in config and config["relationship_types"]:
        try:
            rel_backup = backup_relationships_by_types(config["relationship_types"])
            backup_data.update(rel_backup)
        except Exception as e:
            warning = f"Error backing up relationship types: {e}"
            warnings.append(warning)
            print(f"   ⚠️ {warning}")

    # Backup nodes with their relationships
    if "nodes_with_relationships" in config and config["nodes_with_relationships"]:
        for node_config in config["nodes_with_relationships"]:
            try:
                node_label = node_config["label"]
                rel_types = node_config["relationships"]

                node_rel_backup = backup_node_relationships(node_label, rel_types)
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

    print(f"\n   ✅ Dynamic backup completed: {total_items} items")
    if warnings:
        print(f"   ⚠️ {len(warnings)} warnings occurred")

    return backup_data


def get_unique_property(props: dict[str, any]) -> tuple | None:
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


def restore_nodes(backup_data: dict[str, any]) -> int:
    """Restore nodes from backup data using ORM where possible"""
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

                        # Use ORM for known models, fallback to cypher
                        if label == "User":
                            # Use ORM to create/update User
                            user = User.nodes.get_or_none(email=props.get("email"))
                            if not user:
                                user = User(
                                    uid=props.get("uid"),
                                    name=props.get("name"),
                                    email=props.get("email"),
                                    password=props.get("password"),
                                    profilePicture=props.get("profilePicture"),
                                    role=props.get("role", "user"),
                                )
                                user.save()
                                restored += 1
                        elif label == "ScrapingTask":
                            # Use ORM to create/update ScrapingTask
                            task = ScrapingTask.nodes.get_or_none(uid=props.get("uid"))
                            if not task:
                                task = ScrapingTask(
                                    uid=props.get("uid"),
                                    status=props.get("status"),
                                    startedAt=props.get("startedAt"),
                                    finishedAt=props.get("finishedAt"),
                                    message=props.get("message", ""),
                                )
                                task.save()
                                restored += 1
                        elif label == "MatchingTask":
                            # Use ORM to create/update MatchingTask
                            task = MatchingTask.nodes.get_or_none(uid=props.get("uid"))
                            if not task:
                                task = MatchingTask(
                                    uid=props.get("uid"),
                                    status=props.get("status"),
                                    startedAt=props.get("startedAt"),
                                    finishedAt=props.get("finishedAt"),
                                )
                                task.save()
                                restored += 1
                        elif label == "Maintenance":
                            # Use ORM to create/update Maintenance
                            maintenance = Maintenance.get_current_maintenance()
                            if not maintenance:
                                maintenance = Maintenance(
                                    isMaintenance=props.get("isMaintenance", False)
                                )
                                maintenance.save()
                                restored += 1
                        else:
                            # Fallback to cypher for unknown labels
                            unique_prop = get_unique_property(props)
                            if not unique_prop:
                                print(
                                    f"     ⚠️ No unique property found for {label} node, skipping..."
                                )
                                continue

                            labels_str = ":".join(labels)
                            query = f"""
                            MERGE (n:{labels_str} {{{unique_prop[0]}: $unique_value}})
                            SET n = $props
                            """
                            db.cypher_query(
                                query, {"unique_value": unique_prop[1], "props": props}
                            )
                            restored += 1

                    except Exception as e:
                        print(f"     ⚠️ Error restoring individual {label} node: {e}")
                        continue

                print(f"     ✅ Restored {restored} {label} nodes")
                total_restored += restored

            except Exception as e:
                print(f"     ⚠️ Error restoring {label} nodes: {e}")
                continue

    return total_restored


def restore_relationships(backup_data: dict[str, any]) -> int:
    """Restore relationships from backup data using db.cypher_query"""
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
                        start_match_prop = get_unique_property(start_props)
                        end_match_prop = get_unique_property(end_props)

                        if start_match_prop and end_match_prop:
                            query = f"""
                            MERGE (start:{start_labels_str} {{{start_match_prop[0]}: $start_value}})
                            SET start = $start_props
                            MERGE (end:{end_labels_str} {{{end_match_prop[0]}: $end_value}})
                            SET end = $end_props
                            MERGE (start)-[r:{rel_type}]->(end)
                            SET r = $rel_props
                            """

                            db.cypher_query(
                                query,
                                {
                                    "start_value": start_match_prop[1],
                                    "end_value": end_match_prop[1],
                                    "start_props": start_props,
                                    "end_props": end_props,
                                    "rel_props": rel_props,
                                },
                            )
                            restored += 1
                    except Exception as e:
                        print(
                            f"     ⚠️ Error restoring individual {rel_type} relationship: {e}"
                        )
                        continue

                print(f"     ✅ Restored {restored} {rel_type} relationships")
                total_restored += restored

            except Exception as e:
                print(f"     ⚠️ Error restoring {rel_type} relationships: {e}")
                continue

    return total_restored


def restore_nodes_with_relationships(backup_data: dict[str, any]) -> int:
    """Restore nodes with their relationships using hybrid approach"""
    total_restored = 0

    for key, nodes_with_rels in backup_data.items():
        if key.endswith("_with_relationships") and isinstance(nodes_with_rels, list):
            if not nodes_with_rels:  # Skip empty collections
                continue

            label = key.replace("_with_relationships", "").title()
            print(f"   🎯 Restoring {label} with relationships...")

            restored = 0
            for node_data in nodes_with_rels:
                try:
                    props = node_data["properties"]
                    labels = node_data["labels"]
                    relationships = node_data["relationships"]

                    # Get unique property for main node
                    node_match_prop = get_unique_property(props)
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
                    db.cypher_query(
                        merge_node_query,
                        {"node_value": node_match_prop[1], "props": props},
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
                                    match_prop = get_unique_property(related_props)

                                    if match_prop and node_match_prop:
                                        query = f"""
                                        MERGE (n:{labels_str} {{{node_match_prop[0]}: $node_value}})
                                        MERGE (related:{related_labels_str} {{{match_prop[0]}: $related_value}})
                                        SET related = $related_props
                                        MERGE (n)-[r:{rel_type}]->(related)
                                        SET r = $rel_props
                                        """

                                        db.cypher_query(
                                            query,
                                            {
                                                "node_value": node_match_prop[1],
                                                "related_value": match_prop[1],
                                                "related_props": related_props,
                                                "rel_props": rel_props,
                                            },
                                        )
                                        rel_count += 1

                    print(
                        f"     📎 Restored {rel_count} relationships for {label} node"
                    )
                    restored += 1

                except Exception as e:
                    print(f"     ⚠️ Error restoring {label} node: {e}")
                    continue

            print(f"     ✅ Restored {restored} {label} with relationships")
            total_restored += restored

    return total_restored


def enrich_user_nodes(users_data: list) -> int:
    """Enrich User nodes with additional properties using ORM"""
    if not users_data:
        return 0

    print("👤 Enriching User nodes with additional properties...")
    print(f"   Found {len(users_data)} users in data")

    updated_count = 0
    for user_data in users_data:
        try:
            email = user_data.get("email")
            if not email:
                continue

            # Find user using ORM
            user = User.nodes.get_or_none(email=email)
            if user:
                # Update properties using ORM
                if user_data.get("name"):
                    user.name = user_data["name"]
                if user_data.get("profile_image"):
                    user.profilePicture = user_data["profile_image"]
                if user_data.get("password"):
                    user.password = user_data["password"]

                user.save()
                updated_count += 1
                print(f"     ✅ Updated User: {email}")
            else:
                print(f"     ⚠️ User not found: {email}")

        except Exception as e:
            print(
                f"     ❌ Error updating user {user_data.get('email', 'unknown')}: {e}"
            )
            continue

    print(f"   ✅ Successfully enriched {updated_count} User nodes")
    return updated_count


def enrich_job_nodes(jobs_data: list) -> int:
    """Enrich Job nodes with additional properties using hybrid approach"""
    if not jobs_data:
        return 0

    print("💼 Enriching Job nodes with additional properties...")
    print(f"   Found {len(jobs_data)} jobs in data")

    updated_count = 0
    for job_data in jobs_data:
        try:
            job_url = job_data.get("job_url")
            if not job_url:
                continue

            # Use cypher for job enrichment since Job model might be complex
            additional_props = {
                "imageUrl": job_data.get("image_url"),
                "jobTitle": job_data.get("job_title"),
                "companyName": job_data.get("company_name"),
                "subdistrict": job_data.get("subdistrict"),
                "city": job_data.get("city"),
                "province": job_data.get("province"),
                "minimumSalary": job_data.get("minimum_salary"),
                "maximumSalary": job_data.get("maximum_salary"),
                "employmentType": job_data.get("employment_type"),
                "workSetup": job_data.get("work_setup"),
                "minimumEducation": job_data.get("minimum_education"),
                "minimumExperience": job_data.get("minimum_experience"),
                "maximumExperience": job_data.get("maximum_experience"),
                "jobDescription": job_data.get("job_description"),
                "scrapedAt": job_data.get("scraped_at"),
            }

            # Remove None values
            additional_props = {
                k: v for k, v in additional_props.items() if v is not None
            }

            if additional_props:
                query = """
                MATCH (j:Job {jobUrl: $job_url})
                SET j += $additional_props
                RETURN count(j) AS updated
                """

                result, _ = db.cypher_query(
                    query, {"job_url": job_url, "additional_props": additional_props}
                )
                updated = result[0][0] if result else 0

                if updated > 0:
                    updated_count += 1
                    if updated_count % 100 == 0:
                        print(f"     ✅ Updated {updated_count} jobs...")

        except Exception as e:
            print(
                f"     ❌ Error updating job {job_data.get('job_url', 'unknown')}: {e}"
            )
            continue

    print(f"   ✅ Successfully enriched {updated_count} Job nodes")
    return updated_count


def enrich_nodes_with_data(
    users_data: list[dict] | None = None,
    jobs_data: list[dict] | None = None,
) -> dict:
    """Enrich nodes with additional properties from data variables"""
    print("🔄 Starting node enrichment process...")

    enrichment_stats = {"users_updated": 0, "jobs_updated": 0}

    # Enrich User nodes
    if users_data:
        try:
            users_updated = enrich_user_nodes(users_data)
            enrichment_stats["users_updated"] = users_updated
        except Exception as e:
            print(f"   ❌ Failed to enrich User nodes: {e}")

    # Enrich Job nodes
    if jobs_data:
        try:
            jobs_updated = enrich_job_nodes(jobs_data)
            enrichment_stats["jobs_updated"] = jobs_updated
        except Exception as e:
            print(f"   ❌ Failed to enrich Job nodes: {e}")

    total_updated = enrichment_stats["users_updated"] + enrichment_stats["jobs_updated"]
    print(f"✅ Node enrichment completed: {total_updated} nodes updated")

    return enrichment_stats


def perform_full_dynamic_restore_with_enrichment(
    backup_data: dict[str, any],
    users_data: list[dict] | None = None,
    jobs_data: list[dict] | None = None,
) -> bool:
    """Perform full restore from backup data with node enrichment"""
    if not backup_data or "metadata" not in backup_data:
        print("   ⚠️ No valid backup data to restore")
        return False

    print(f"   🔄 Restoring data from {backup_data['metadata']['backup_timestamp']}")

    try:
        db.begin()
        try:
            total_restored = 0

            # Step 1: Restore nodes first
            total_restored += restore_nodes(backup_data)

            # Step 2: Restore standalone relationships
            total_restored += restore_relationships(backup_data)

            # Step 3: Restore nodes with their relationships
            total_restored += restore_nodes_with_relationships(backup_data)

            print(f"   ✅ Dynamic restore completed: {total_restored} items restored")

            # Step 4: Enrich nodes with additional properties
            if users_data or jobs_data:
                print("   🎯 Starting node enrichment...")
                enrichment_stats = enrich_nodes_with_data(users_data, jobs_data)

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

            db.commit()
            print("   ✅ Restore transaction committed successfully")
            return True

        except Exception as e:
            db.rollback()
            print(f"   ❌ Error during restore, transaction rolled back: {e}")
            return False

    except Exception as e:
        print(f"   ❌ Error during restore with enrichment: {e}")
        return False
