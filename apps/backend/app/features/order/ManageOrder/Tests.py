import pytest
from unittest.mock import Mock

from .Handler import ManageOrderHandler


class TestManageOrderHandler:

    def test_raises_without_session(self):
        handler = ManageOrderHandler()
        with pytest.raises(ValueError, match="Authenticated broker session required"):
            handler.execute(
                tradingsymbol="ITBEES",
                exchange="BSE",
                transaction_type="BUY",
                quantity=33,
                price=245.50,
            )

    def test_raises_on_empty_tradingsymbol(self):
        handler = ManageOrderHandler()
        with pytest.raises(ValueError, match="Missing required order fields"):
            handler.execute(
                tradingsymbol="",
                exchange="BSE",
                transaction_type="BUY",
                quantity=33,
                price=245.50,
                broker_session=Mock(),
            )

    def test_raises_on_zero_quantity(self):
        handler = ManageOrderHandler()
        with pytest.raises(ValueError, match="Quantity must be positive"):
            handler.execute(
                tradingsymbol="ITBEES",
                exchange="BSE",
                transaction_type="BUY",
                quantity=0,
                price=245.50,
                broker_session=Mock(),
            )

    def test_raises_on_zero_price(self):
        handler = ManageOrderHandler()
        with pytest.raises(ValueError, match="Price must be positive"):
            handler.execute(
                tradingsymbol="ITBEES",
                exchange="BSE",
                transaction_type="BUY",
                quantity=33,
                price=0,
                broker_session=Mock(),
            )

    def test_places_cnc_order_successfully(self):
        mock_session = Mock()
        mock_session.order_place.return_value = "ORD12345"
        handler = ManageOrderHandler()
        result = handler.execute(
            tradingsymbol="ITBEES",
            exchange="BSE",
            transaction_type="BUY",
            quantity=33,
            price=245.50,
            broker_session=mock_session,
        )
        assert result["status"] == "ok"
        assert result["order_id"] == "ORD12345"
        mock_session.order_place.assert_called_once_with(
            tradingsymbol="ITBEES",
            exchange="BSE",
            side="BUY",
            quantity=33,
            order_type="LIMIT",
            product="C",
            variety="regular",
            price=245.50,
        )

    def test_handles_broker_failure_gracefully(self):
        mock_session = Mock()
        mock_session.order_place.side_effect = Exception("Insufficient margin")
        handler = ManageOrderHandler()
        result = handler.execute(
            tradingsymbol="ITBEES",
            exchange="BSE",
            transaction_type="BUY",
            quantity=33,
            price=245.50,
            broker_session=mock_session,
        )
        assert result["status"] == "error"
        assert "Insufficient margin" in result["message"]
