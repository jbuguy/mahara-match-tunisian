from fastapi import FastAPI

from app.features.employer.market import router as employer_market_router


def test_salary_benchmark_canonical_route_and_deprecated_alias_are_documented():
    app = FastAPI()
    app.include_router(employer_market_router)
    paths = app.openapi()["paths"]

    canonical = paths["/api/v1/employer/salaries"]["get"]
    legacy = paths["/api/v1/employer/market/salaries"]["get"]

    assert canonical["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/SalaryBenchmarkOut"
    )
    assert legacy["deprecated"] is True
    assert legacy["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/SalaryBenchmarkOut"
    )
    benchmark_schema = app.openapi()["components"]["schemas"]["SalaryBenchmarkOut"]
    assert benchmark_schema["properties"]["status"]["enum"] == [
        "available",
        "suppressed",
        "unavailable",
    ]
