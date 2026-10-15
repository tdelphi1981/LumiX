"""W7: utilities (rational conversion, exports, logging)."""

import io
import logging
from fractions import Fraction

import pytest

import lumix
from lumix import LXLinearExpression, LXModel, LXOptimizer, LXVariable
from lumix.utils import LXRationalConverter


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.5, Fraction(1, 2)),
        (-0.5, Fraction(-1, 2)),
        (2.333, Fraction(2333, 1000)),
        (-2.75, Fraction(-11, 4)),
        (3.14159, Fraction(9563, 3044)),
        (0.1, Fraction(1, 10)),
        (-0.1, Fraction(-1, 10)),
        (0.9999, Fraction(9999, 10000)),
        (1e-7, Fraction(0)),
        (-1e-7, Fraction(0)),
        (7.0, Fraction(7)),
    ],
)
def test_b13_continued_fraction_converges(value, expected):
    conv = LXRationalConverter(max_denominator=10000, method="continued_fraction")
    assert conv.to_rational(value) == expected


def test_b13_continued_fraction_respects_max_denominator():
    conv = LXRationalConverter(max_denominator=100, method="continued_fraction")
    frac = conv.to_rational(3.14159265)
    assert frac == Fraction(311, 99) or frac == Fraction(22, 7)
    assert frac.denominator <= 100


def test_b17_documented_top_level_imports():
    import lumix
    from lumix import CPSAT_CAPABILITIES, GLPK_CAPABILITIES, LXPiecewiseLinearizer, LXRowKeyFilter

    assert CPSAT_CAPABILITIES.name and GLPK_CAPABILITIES.name
    assert LXPiecewiseLinearizer.__name__ == "LXPiecewiseLinearizer"
    assert LXRowKeyFilter.__name__ == "LXRowKeyFilter"
    for name in ("CPSAT_CAPABILITIES", "GLPK_CAPABILITIES", "LXPiecewiseLinearizer", "LXRowKeyFilter"):
        assert name in lumix.__all__




def _tiny_model():
    x = LXVariable[str, float]("x").continuous().bounds(lower=0, upper=1).indexed_by(lambda s: s).from_data(["k"])
    return LXModel("m").add_variable(x).maximize(LXLinearExpression().add_term(x, lambda s: 1))


@pytest.fixture
def clean_lumix_logging():
    names = ("lumix", "lumix.optimizer", "lumix.ortools")
    saved = {n: (logging.getLogger(n).level, list(logging.getLogger(n).handlers)) for n in names}
    yield
    for n, (level, handlers) in saved.items():
        lg = logging.getLogger(n)
        lg.setLevel(level)
        lg.handlers[:] = handlers


def test_b16_library_adds_only_a_null_handler(clean_lumix_logging):
    LXOptimizer().use_solver("ortools").solve(_tiny_model())
    root = logging.getLogger("lumix")
    assert any(isinstance(h, logging.NullHandler) for h in root.handlers)
    for name in ("lumix", "lumix.optimizer", "lumix.ortools"):
        handlers = logging.getLogger(name).handlers
        assert [h for h in handlers if not isinstance(h, logging.NullHandler)] == []


def test_b16_new_optimizer_keeps_the_applications_level(clean_lumix_logging):
    logging.getLogger("lumix.optimizer").setLevel(logging.WARNING)
    LXOptimizer()
    assert logging.getLogger("lumix.optimizer").level == logging.WARNING


def test_b16_each_record_reaches_the_application_once(clean_lumix_logging, caplog):
    with caplog.at_level(logging.INFO, logger="lumix"):
        LXOptimizer().use_solver("ortools").solve(_tiny_model())
    starts = [r for r in caplog.records if r.getMessage().startswith("Starting solve")]
    assert len(starts) == 1


def test_w7_enable_logging_prints_once_and_is_idempotent(clean_lumix_logging):
    buf = io.StringIO()
    lumix.enable_logging("DEBUG", stream=io.StringIO())
    handler = lumix.enable_logging("INFO", stream=buf)
    own = [h for h in logging.getLogger("lumix").handlers if getattr(h, "_lumix_console", False)]
    assert own == [handler]
    assert logging.getLogger("lumix").level == logging.INFO
    LXOptimizer().use_solver("ortools").solve(_tiny_model())
    assert buf.getvalue().count("Starting solve with ortools") == 1


def test_w7_model_logger_sets_level_only_when_asked(clean_lumix_logging):
    from lumix.utils import LXModelLogger

    logging.getLogger("lumix.optimizer").setLevel(logging.ERROR)
    LXModelLogger("lumix.optimizer")
    assert logging.getLogger("lumix.optimizer").level == logging.ERROR
    LXModelLogger("lumix.optimizer", level=logging.DEBUG)
    assert logging.getLogger("lumix.optimizer").level == logging.DEBUG
