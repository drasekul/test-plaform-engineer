# tests/unit/test_ports.py
# Tests de los puertos del dominio.
# Verifican que los contratos abstractos se hacen cumplir en tiempo de instanciación,
# garantizando que ningún adaptador pueda omitir métodos requeridos.
import pytest

from src.domain.ports import DataRepository, MessagePublisher


@pytest.mark.unit
class TestMessagePublisher:

    def test_cannot_instantiate_abstract_class_directly(self):
        # Instanciar un ABC directamente debe lanzar TypeError
        with pytest.raises(TypeError):
            MessagePublisher()

    def test_subclass_without_publish_cannot_be_instantiated(self):
        # Un adaptador que no implementa publish no puede instanciarse
        class IncompletePublisher(MessagePublisher):
            pass
        with pytest.raises(TypeError):
            IncompletePublisher()

    def test_concrete_subclass_with_publish_can_be_instantiated(self):
        # Un adaptador correcto sí puede instanciarse
        class ConcretePublisher(MessagePublisher):
            def publish(self, sale):
                return "msg-id"
        publisher = ConcretePublisher()
        assert publisher is not None


@pytest.mark.unit
class TestDataRepository:

    def test_cannot_instantiate_abstract_class_directly(self):
        with pytest.raises(TypeError):
            DataRepository()

    def test_subclass_without_save_cannot_be_instantiated(self):
        class IncompleteRepository(DataRepository):
            pass
        with pytest.raises(TypeError):
            IncompleteRepository()

    def test_concrete_subclass_with_save_can_be_instantiated(self):
        class ConcreteRepository(DataRepository):
            def save(self, sale):
                pass
        repo = ConcreteRepository()
        assert repo is not None
