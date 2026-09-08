"""
Database Utility Module
=======================
Provides functions to connect to PostgreSQL and persist generated page data
into the "MST_Page" table. Supports INSERT (new slug) and UPDATE (existing slug).

Configuration via environment variables:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import psycopg2
from datetime import datetime


def _get_credentials():
    """Read database credentials from environment variables."""
    return {
        "host": os.environ.get("DB_HOST", ""),
        "port": int(os.environ.get("DB_PORT", 5432)),
        "database": os.environ.get("DB_NAME", ""),
        "user": os.environ.get("DB_USER", ""),
        "password": os.environ.get("DB_PASSWORD", ""),
    }


def _connect():
    """Create and return a psycopg2 connection using environment credentials."""
    creds = _get_credentials()
    if not creds["host"] or not creds["database"] or not creds["user"]:
        raise ValueError(
            "Database credentials incomplete. "
            "Set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD in your .env file."
        )
    return psycopg2.connect(
        host=creds["host"],
        port=creds["port"],
        database=creds["database"],
        user=creds["user"],
        password=creds["password"],
    )


def get_config_status():
    """
    Return whether database credentials are configured (without exposing secrets).
    """
    creds = _get_credentials()
    configured = bool(creds["host"] and creds["database"] and creds["user"])
    return {
        "configured": configured,
        "host": creds["host"] or "(not set)",
        "port": creds["port"],
        "database": creds["database"] or "(not set)",
        "user": creds["user"] or "(not set)",
    }


def test_connection():
    """
    Test database connectivity. Returns (success: bool, message: str).
    """
    try:
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


def save_page_to_db(page_data: dict) -> dict:
    """
    Insert or update a page in the "MST_Page" table based on slug existence.

    Expected keys in page_data:
        page_title, slug, page_type, meta_title, meta_description,
        keywords, og_title, og_description, og_image_url,
        publish_datetime, is_active,
        html_content, schema_script, css_content, js_content
    """
    conn = _connect()
    cursor = conn.cursor()

    slug = page_data.get("slug", "").strip()
    if not slug:
        raise ValueError("URL Slug is required to publish a page.")

    page_title = page_data.get("page_title", "")
    page_type = page_data.get("page_type", "")
    meta_title = page_data.get("meta_title", "")
    meta_description = page_data.get("meta_description", "")
    keywords = page_data.get("keywords", "")
    og_title = page_data.get("og_title", "")
    og_description = page_data.get("og_description", "")
    og_image_url = page_data.get("og_image_url", "")
    is_active = page_data.get("is_active", True)
    html_content = page_data.get("html_content", "")
    schema_script = page_data.get("schema_script", "")
    css_content = page_data.get("css_content", "")
    js_content = page_data.get("js_content", "")

    # Parse publish_datetime
    publish_dt_raw = page_data.get("publish_datetime", "")
    if publish_dt_raw:
        try:
            publish_datetime = datetime.fromisoformat(publish_dt_raw)
        except (ValueError, TypeError):
            publish_datetime = datetime.now()
    else:
        publish_datetime = datetime.now()

    try:
        # Check if page already exists by Slug
        cursor.execute('SELECT "PageID" FROM "MST_Page" WHERE "Slug" = %s', (slug,))
        existing_row = cursor.fetchone()

        if existing_row:
            page_id = existing_row[0]
            sql = """
            UPDATE "MST_Page" SET
                "Title"           = %s,
                "PageType"        = %s,
                "MetaTitle"       = %s,
                "MetaDescription" = %s,
                "MetaKeywords"    = %s,
                "OGTitle"         = %s,
                "OGDescription"   = %s,
                "TwitterCard"     = %s,
                "PublishDateTme"  = %s,
                "IsActive"        = %s,
                "Content"         = %s,
                "SchemaTypes"     = %s,
                "CustomCss"       = %s,
                "CustomJs"        = %s,
                "UpdatedAt"       = NOW()
            WHERE "PageID" = %s
            """
            cursor.execute(sql, (
                page_title, page_type, meta_title, meta_description,
                keywords, og_title, og_description, og_image_url,
                publish_datetime, is_active, html_content, schema_script,
                css_content, js_content, page_id
            ))
            conn.commit()
            action = "UPDATE"
        else:
            sql = """
            INSERT INTO "MST_Page" (
                "Title", "Slug", "PageType", "MetaTitle", "MetaDescription",
                "MetaKeywords", "OGTitle", "OGDescription", "TwitterCard",
                "PublishDateTme", "IsActive", "IsDeleted", "Content",
                "SchemaTypes", "CustomCss", "CustomJs", "CreatedAt", "UpdatedAt"
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, %s, %s, NOW(), NOW()
            ) RETURNING "PageID"
            """
            cursor.execute(sql, (
                page_title, slug, page_type, meta_title, meta_description,
                keywords, og_title, og_description, og_image_url,
                publish_datetime, is_active, html_content, schema_script,
                css_content, js_content
            ))
            result = cursor.fetchone()
            page_id = result[0] if result else None
            conn.commit()
            action = "INSERT"

        cursor.close()
        conn.close()

        return {
            "success": True,
            "action": action,
            "page_id": page_id,
            "slug": slug,
            "message": f"Page '{slug}' {'updated' if action == 'UPDATE' else 'inserted'} successfully (ID: {page_id})"
        }

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise e


def add_page_image_to_db(image_url: str) -> dict:
    """
    Insert a single image record into the "PAG_PagesImages" table.

    Args:
        image_url: The public URL of the uploaded image.

    Returns:
        dict with keys: success, image_id, image_url, message
    """
    conn = _connect()
    cursor = conn.cursor()
    try:
        sql = """
        INSERT INTO "PAG_PagesImages" ("ImageLink", "CreatedAt", "IsDeleted")
        VALUES (%s, NOW(), FALSE)
        RETURNING "ImageID"
        """
        cursor.execute(sql, (image_url,))
        result = cursor.fetchone()
        image_id = result[0] if result else None
        conn.commit()
        cursor.close()
        conn.close()
        return {
            "success": True,
            "image_id": image_id,
            "image_url": image_url,
            "message": f"Image saved (ID: {image_id})",
        }
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise e


def add_page_images_bulk(image_urls: list) -> list:
    """
    Insert multiple image records into "PAG_PagesImages" in a single transaction.

    Args:
        image_urls: List of public URLs.

    Returns:
        List of dicts with keys: success, image_id, image_url
    """
    if not image_urls:
        return []

    conn = _connect()
    cursor = conn.cursor()
    results = []
    try:
        for url in image_urls:
            sql = """
            INSERT INTO "PAG_PagesImages" ("ImageLink", "CreatedAt", "IsDeleted")
            VALUES (%s, NOW(), FALSE)
            RETURNING "ImageID"
            """
            cursor.execute(sql, (url,))
            row = cursor.fetchone()
            results.append({
                "success": True,
                "image_id": row[0] if row else None,
                "image_url": url,
            })
        conn.commit()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise e
