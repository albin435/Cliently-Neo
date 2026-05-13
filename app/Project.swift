import ProjectDescription

let project = Project(
    name: "Neo",
    options: .options(
        defaultKnownRegions: ["en"],
        developmentRegion: "en"
    ),
    targets: [
        .target(
            name: "Neo",
            destinations: [.mac, .iPhone, .iPad],
            product: .app,
            bundleId: "com.cliently.neo",
            deploymentTargets: .multiplatform(iOS: "17.0", macOS: "14.0"),
            infoPlist: .extendingDefault(with: [
                "CFBundleDisplayName": "Neo",
                "CFBundleName": "Neo",
                "LSUIElement": false,
                "LSApplicationCategoryType": "public.app-category.developer-tools",
                "NSAppTransportSecurity": [
                    "NSAllowsLocalNetworking": true,
                    "NSAllowsArbitraryLoads": true
                ],
            ]),
            sources: ["Sources/**"],
            resources: ["Resources/**"],
            settings: .settings(
                base: [
                    "SWIFT_VERSION": "5.9",
                ]
            )
        ),
    ]
)
