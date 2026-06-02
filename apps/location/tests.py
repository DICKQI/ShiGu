from __future__ import annotations

from django.test import TestCase
from rest_framework import status

from apps._test_helpers import (
    auth_client,
    create_admin_user,
    create_goods,
    create_storage_node,
    create_user,
)
from apps.location.models import StorageNode


class StorageNodeApiTestCase(TestCase):
    def setUp(self):
        self.user = create_user(username="location_user")
        self.other_user = create_user(username="other_location_user")
        self.admin = create_admin_user(username="location_admin")
        self.client = auth_client(self.user)
        self.other_client = auth_client(self.other_user)
        self.admin_client = auth_client(self.admin)

    def test_list_create_and_detail_are_scoped_to_current_user(self):
        own_node = create_storage_node(self.user, name="Own Room")
        create_storage_node(self.other_user, name="Other Room")

        list_response = self.client.get("/api/location/nodes/")
        detail_response = self.client.get(f"/api/location/nodes/{own_node.id}/")
        other_detail_response = self.client.get(f"/api/location/nodes/{own_node.id}/")
        other_user_response = self.other_client.get(f"/api/location/nodes/{own_node.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.json()), 1)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_user_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_generates_path_name_and_limits_parent_to_owner(self):
        root_response = self.client.post(
            "/api/location/nodes/",
            {"name": "Room", "order": 1},
            format="json",
        )
        self.assertEqual(root_response.status_code, status.HTTP_201_CREATED)
        root_id = root_response.json()["id"]
        self.assertEqual(root_response.json()["path_name"], "Room")

        child_response = self.client.post(
            "/api/location/nodes/",
            {"name": "Shelf", "parent": root_id},
            format="json",
        )
        other_parent = create_storage_node(self.other_user, name="Forbidden Parent")
        forbidden_response = self.client.post(
            "/api/location/nodes/",
            {"name": "Bad Child", "parent": other_parent.id},
            format="json",
        )

        self.assertEqual(child_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(child_response.json()["path_name"], "Room/Shelf")
        self.assertEqual(forbidden_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_regenerates_path_name_when_name_or_parent_changes(self):
        root = create_storage_node(self.user, name="Room")
        other_root = create_storage_node(self.user, name="Studio")
        child = create_storage_node(self.user, name="Shelf", parent=root)

        rename_response = self.client.patch(
            f"/api/location/nodes/{child.id}/",
            {"name": "Drawer"},
            format="json",
        )
        move_response = self.client.patch(
            f"/api/location/nodes/{child.id}/",
            {"parent": other_root.id},
            format="json",
        )

        self.assertEqual(rename_response.status_code, status.HTTP_200_OK)
        self.assertEqual(rename_response.json()["path_name"], "Room/Drawer")
        self.assertEqual(move_response.status_code, status.HTTP_200_OK)
        self.assertEqual(move_response.json()["path_name"], "Studio/Drawer")

    def test_tree_returns_only_current_user_nodes_but_admin_sees_all(self):
        create_storage_node(self.user, name="Own Room")
        create_storage_node(self.other_user, name="Other Room")

        user_response = self.client.get("/api/location/tree/")
        admin_response = self.admin_client.get("/api/location/tree/")

        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(user_response.json()), 1)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_response.json()), 2)

    def test_node_goods_supports_include_children_and_user_scope(self):
        root = create_storage_node(self.user, name="Room")
        child = create_storage_node(self.user, name="Shelf", parent=root)
        direct_goods = create_goods(self.user, name="Direct Goods", location=root)
        child_goods = create_goods(self.user, name="Child Goods", location=child)
        create_goods(self.other_user, name="Other Goods", location=create_storage_node(self.other_user))

        direct_response = self.client.get(f"/api/location/nodes/{root.id}/goods/")
        include_children_response = self.client.get(
            f"/api/location/nodes/{root.id}/goods/?include_children=true"
        )

        self.assertEqual(direct_response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["name"] for item in direct_response.json()}, {direct_goods.name})
        self.assertEqual(include_children_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["name"] for item in include_children_response.json()},
            {direct_goods.name, child_goods.name},
        )

    def test_destroy_deletes_descendants_and_nulls_related_goods_location(self):
        root = create_storage_node(self.user, name="Room")
        child = create_storage_node(self.user, name="Shelf", parent=root)
        goods = create_goods(self.user, location=child)

        response = self.client.delete(f"/api/location/nodes/{root.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StorageNode.objects.filter(id__in=[root.id, child.id]).exists())
        goods.refresh_from_db()
        self.assertIsNone(goods.location_id)

    def test_protected_endpoints_require_authentication(self):
        response = auth_client().get("/api/location/nodes/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
