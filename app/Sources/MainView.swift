import SwiftUI
#if os(macOS)
import AppKit
#else
import UIKit
#endif

// MARK: - Design System

enum NeoTheme {
    static let accent = Color.accentColor
    static let primaryText = Color.primary
    static let secondaryText = Color.secondary
    
    static let surface = Color.primary.opacity(0.04)
    static let border = Color.primary.opacity(0.1)
    
    static let glassBackground = Color.primary.opacity(0.03)
    
    static let neonGreen = Color(red: 0.2, green: 0.9, blue: 0.5)
    static let neonOrange = Color(red: 1.0, green: 0.6, blue: 0.2)
    static let telegramBlue = Color(red: 0.2, green: 0.6, blue: 1.0)
    
    static let shadow = Color.black.opacity(0.1)
}


// MARK: - Blur View

#if os(macOS)
struct BlurView: NSViewRepresentable {
    var material: NSVisualEffectView.Material
    var blendingMode: NSVisualEffectView.BlendingMode

    func makeNSView(context: Context) -> NSVisualEffectView {
        let v = NSVisualEffectView()
        v.material = material
        v.blendingMode = blendingMode
        v.state = .active
        return v
    }
    func updateNSView(_ v: NSVisualEffectView, context: Context) {
        v.material = material
        v.blendingMode = blendingMode
    }
}
#else
struct BlurView: UIViewRepresentable {
    func makeUIView(context: Context) -> UIVisualEffectView {
        let view = UIVisualEffectView(effect: UIBlurEffect(style: .systemChromeMaterial))
        return view
    }
    func updateUIView(_ uiView: UIVisualEffectView, context: Context) {}
}
#endif


// MARK: - Main View

struct MainView: View {
    @State private var store = Store()
    @State private var promptText: String = ""
    @State private var showContextPanel: Bool = true
    @State private var enginePulse: Bool = false
    @State private var showSettings: Bool = false
    @State private var selectedView: NeoView = .chat

    enum NeoView: String, CaseIterable {
        case chat = "Chat"
        case history = "Execution History"
        case memory = "Memory Bank"
        case workspaces = "Project Workspaces"
    }

    private let models = [
        ("gemini-2.5-flash", "Flash"),
        ("gemini-2.5-pro", "Pro"),
    ]

    var body: some View {
        NavigationSplitView {
            SidebarView(store: store, selectedView: $selectedView, showSettings: $showSettings)
        } detail: {
            HStack(spacing: 0) {
                VStack(spacing: 0) {
                    headerBar
                    Divider().opacity(0.12)
                    
                    switch selectedView {
                    case .chat:
                        chatView
                    case .history:
                        HistoryView(store: store)
                    case .memory:
                        MemoryBankView(store: store)
                    case .workspaces:
                        WorkspacesView(store: store)
                    }
                }
                .background(Color.primary.opacity(0.01))

                if showContextPanel {
                    Divider().opacity(0.12)
                    ContextPanelView(store: store)
                        .frame(width: 260)
                        .transition(.move(edge: .trailing))
                }
            }
        }
        .frame(minWidth: 800, idealWidth: 1100, minHeight: 550, idealHeight: 750)
        #if os(macOS)
        .background(Color(NSColor.windowBackgroundColor))
        #else
        .background(Color(UIColor.systemBackground))
        #endif
        .onAppear {
            store.connect()
            enginePulse = true
        }
        .animation(.easeInOut(duration: 0.25), value: store.taskActive)
        .animation(.easeInOut(duration: 0.2), value: showContextPanel)
        .sheet(isPresented: $showSettings) {
            SettingsView(store: store, isPresented: $showSettings)
        }
        // Keyboard Shortcuts
        .background(
            Button("") { showContextPanel.toggle() }
                .keyboardShortcut("\\", modifiers: .command)
                .hidden()
        )
        .background(
            Button("") { showSettings.toggle() }
                .keyboardShortcut(",", modifiers: .command)
                .hidden()
        )
    }

    // MARK: - Header

    private var headerBar: some View {
        HStack(spacing: 10) {
            ZStack {
                Circle()
                    .fill(store.isConnected ? NeoTheme.neonGreen : NeoTheme.neonOrange)
                    .frame(width: 8, height: 8)
                    .shadow(color: (store.isConnected ? NeoTheme.neonGreen : NeoTheme.neonOrange).opacity(0.6), radius: 4)
                
                Circle()
                    .stroke(store.isConnected ? NeoTheme.neonGreen : NeoTheme.neonOrange, lineWidth: 1.5)
                    .frame(width: 8, height: 8)
                    .scaleEffect(enginePulse ? 2.8 : 1.0)
                    .opacity(enginePulse ? 0.0 : 0.4)
                    .animation(
                        .easeOut(duration: 1.8).repeatForever(autoreverses: false),
                        value: enginePulse
                    )
            }

            Text(store.isConnected ? "Neo Online" : "Connecting...")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(store.isConnected ? .primary : .secondary)

            if !store.branch.isEmpty {
                HStack(spacing: 4) {
                    Text("·").foregroundColor(.secondary.opacity(0.3))
                    Image(systemName: "arrow.triangle.branch")
                        .font(.system(size: 8))
                        .foregroundColor(.accentColor.opacity(0.7))
                    Text(store.branch)
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(.secondary.opacity(0.8))
                }
            }

            if let activeSession = store.sessions.first(where: { $0.id == store.activeSessionId }), activeSession.isTelegram {
                HStack(spacing: 4) {
                    Text("·").foregroundColor(.secondary.opacity(0.3))
                    HStack(spacing: 5) {
                        Image(systemName: "paperplane.fill")
                            .font(.system(size: 8))
                        Text("Telegram Synced")
                            .font(.system(size: 10, weight: .black))
                    }
                    .foregroundColor(NeoTheme.telegramBlue)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(NeoTheme.telegramBlue.opacity(0.12))
                    .clipShape(Capsule())
                }
            }

            Spacer()

            Menu {
                ForEach(models, id: \.0) { id, label in
                    Button(action: { store.selectedModel = id }) {
                        HStack {
                            Text(label)
                            if id == store.selectedModel {
                                Image(systemName: "checkmark")
                            }
                        }
                    }
                }
            } label: {
                HStack(spacing: 6) {
                    Image(systemName: "cpu")
                        .font(.system(size: 10))
                    Text(models.first(where: { $0.0 == store.selectedModel })?.1 ?? "Flash")
                        .font(.system(size: 11, weight: .semibold))
                    Image(systemName: "chevron.down")
                        .font(.system(size: 8, weight: .bold))
                }
                .foregroundColor(.secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.primary.opacity(0.06))
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                        )
                )
            }
            .menuStyle(.borderlessButton)
            .fixedSize()

            Button(action: { showContextPanel.toggle() }) {
                Image(systemName: "sidebar.right")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)

            Button(action: { showSettings = true }) {
                Image(systemName: "gearshape.fill")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)

            Button(action: { store.connect() }) {
                Image(systemName: "arrow.triangle.2.circlepath")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
    }

    // MARK: - Pipeline Bar

    private var pipelineBar: some View {
        HStack(spacing: 12) {
            ProgressView()
                .controlSize(.small)
                .scaleEffect(0.8)

            HStack(spacing: 12) {
                phaseDot("Plan", phase: "planning")
                phaseArrow
                phaseDot("Approve", phase: "awaiting_approval")
                phaseArrow
                phaseDot("Delegate", phase: "delegating")
                phaseArrow
                phaseDot("Execute", phase: "executing")
                phaseArrow
                phaseDot("Review", phase: "reviewing")
            }

            Spacer()

            if !store.taskStatusText.isEmpty {
                Text(store.taskStatusText)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(.accentColor)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.accentColor.opacity(0.1))
                    .clipShape(Capsule())
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 10)
        .background(
            ZStack {
                BlurView(material: .titlebar, blendingMode: .withinWindow)
                Color.accentColor.opacity(0.04)
            }
        )
        .overlay(
            Rectangle()
                .fill(Color.primary.opacity(0.05))
                .frame(height: 1),
            alignment: .top
        )
    }

    private var phaseArrow: some View {
        Image(systemName: "chevron.right")
            .font(.system(size: 7))
            .foregroundColor(.secondary.opacity(0.3))
    }

    private func phaseDot(_ label: String, phase: String) -> some View {
        let order = ["planning": 1, "awaiting_approval": 2, "delegating": 3, "executing": 4, "reviewing": 5]
        let current = order[store.taskPhase] ?? 0
        let target = order[phase] ?? 0
        let isActive = store.taskPhase == phase
        let isPast = current > target

        return HStack(spacing: 5) {
            ZStack {
                Circle()
                    .fill(isActive ? Color.accentColor : (isPast ? Color.green : Color.primary.opacity(0.1)))
                    .frame(width: 6, height: 6)
                
                if isActive {
                    Circle()
                        .stroke(Color.accentColor, lineWidth: 1)
                        .frame(width: 10, height: 10)
                        .opacity(0.5)
                }
            }
            Text(label.uppercased())
                .font(.system(size: 9, weight: .black))
                .foregroundColor(isActive ? .primary : (isPast ? .primary.opacity(0.7) : .secondary.opacity(0.5)))
        }
    }

    // MARK: - Chat View

    private var chatView: some View {
        VStack(spacing: 0) {
            chatFeed
            
            if store.taskActive {
                pipelineBar
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
            
            inputArea
        }
    }

    // MARK: - Chat Feed

    private var chatFeed: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(store.messages) { message in
                        MessageBubbleView(message: message, store: store)
                            .id(message.id)
                    }

                    if store.isProcessing || store.taskActive {
                        HStack(spacing: 10) {
                            HStack(spacing: 4) {
                                ForEach(0..<3, id: \.self) { i in
                                    Circle()
                                        .fill(Color.accentColor)
                                        .frame(width: 5, height: 5)
                                        .scaleEffect(enginePulse ? 1.0 : 0.4)
                                        .opacity(enginePulse ? 1.0 : 0.3)
                                        .animation(
                                            .easeInOut(duration: 0.5)
                                            .repeatForever()
                                            .delay(Double(i) * 0.12),
                                            value: enginePulse
                                        )
                                }
                            }
                            Text(store.taskActive ? store.taskStatusText : "Processing...")
                                .font(.system(size: 12))
                                .foregroundColor(.secondary)
                            Spacer()
                        }
                        .padding(.horizontal, 24)
                        .padding(.vertical, 12)
                    }
                }
                .padding(.vertical, 16)
            }
            .onChange(of: store.messages.count) {
                if let last = store.messages.last {
                    withAnimation(.easeOut(duration: 0.15)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: - Input Area

    private var inputArea: some View {
        VStack(spacing: 0) {
            Divider().opacity(0.08)
            HStack(alignment: .bottom, spacing: 10) {
                TextField(
                    store.inputLocked ? "Neo is working..." : "Message Neo...",
                    text: $promptText,
                    axis: .vertical
                )
                .font(.system(size: 13))
                .lineLimit(1...6)
                .textFieldStyle(.plain)
                .padding(10)
                .background(Color.primary.opacity(store.inputLocked ? 0.02 : 0.04))
                .cornerRadius(10)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(Color.primary.opacity(0.06), lineWidth: 1)
                )
                .disabled(store.inputLocked)
                .onSubmit { submitPrompt() }

                Button(action: submitPrompt) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(canSend ? Color.accentColor : .secondary.opacity(0.2))
                }
                .buttonStyle(.plain)
                .disabled(!canSend)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        #if os(macOS)
        .background(BlurView(material: .titlebar, blendingMode: .withinWindow))
        #else
        .background(BlurView())
        #endif
    }

    private var canSend: Bool {
        !store.inputLocked && !promptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func submitPrompt() {
        guard canSend else { return }
        store.send(promptText)
        promptText = ""
    }
}


// MARK: - Sidebar

struct SidebarView: View {
    var store: Store
    @Binding var selectedView: MainView.NeoView
    @Binding var showSettings: Bool

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                ZStack {
                    Circle()
                        .fill(Color.accentColor.opacity(0.1))
                        .frame(width: 32, height: 32)
                    Image(systemName: "cpu.fill")
                        .font(.system(size: 16))
                        .foregroundColor(.accentColor)
                }
                
                VStack(alignment: .leading, spacing: 0) {
                    Text("NEO")
                        .font(.system(size: 14, weight: .black))
                    Text("v2.0 Desktop")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.secondary.opacity(0.6))
                }
                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.top, 24)
            .padding(.bottom, 20)

            Button(action: { store.createSession() }) {
                HStack(spacing: 10) {
                    Image(systemName: "plus")
                        .font(.system(size: 11, weight: .bold))
                    Text("NEW SESSION")
                        .font(.system(size: 11, weight: .black))
                    Spacer()
                    Text("⌘N")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .opacity(0.4)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(Color.accentColor)
                .foregroundColor(.white)
                .cornerRadius(10)
                .shadow(color: Color.accentColor.opacity(0.3), radius: 6, y: 3)
                .padding(.horizontal, 16)
            }
            .buttonStyle(.plain)
            .keyboardShortcut("n", modifiers: .command)
            .padding(.bottom, 16)

            List {
                Section {
                    ForEach(store.sessions, id: \.id) { session in
                        HStack(spacing: 12) {
                            ZStack(alignment: .bottomTrailing) {
                                let iconName = session.isTelegram ? "paperplane.circle.fill" : "bubble.left.and.bubble.right.fill"
                                let isActive = store.activeSessionId == session.id
                                Image(systemName: iconName)
                                    .font(.system(size: 11))
                                    .foregroundColor(isActive ? .accentColor : .secondary.opacity(0.4))
                                
                                if session.isTelegram {
                                    Image(systemName: "bolt.fill")
                                        .font(.system(size: 6))
                                        .foregroundColor(.blue)
                                        .offset(x: 2, y: 2)
                                }
                            }
                            
                            VStack(alignment: .leading, spacing: 3) {
                                HStack(spacing: 4) {
                                    Text(session.title)
                                        .font(.system(size: 12, weight: store.activeSessionId == session.id ? .semibold : .medium))
                                        .lineLimit(1)
                                    
                                    if session.isTelegram {
                                        Text("TG")
                                            .font(.system(size: 7, weight: .bold))
                                            .padding(.horizontal, 3)
                                            .padding(.vertical, 1)
                                            .background(Color.blue.opacity(0.2))
                                            .foregroundColor(.blue)
                                            .cornerRadius(3)
                                    }
                                }
                                
                                Text(formatDate(session.updated_at))
                                    .font(.system(size: 9))
                                    .foregroundColor(.secondary.opacity(0.5))
                            }
                            Spacer()
                            if store.activeSessionId == session.id && store.taskActive {
                                Circle().fill(Color.accentColor).frame(width: 5, height: 5)
                            }
                        }
                        .padding(.vertical, 6)
                        .padding(.horizontal, 8)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(store.activeSessionId == session.id ? Color.accentColor.opacity(0.12) : Color.clear)
                        )
                        .contentShape(Rectangle())
                        .onTapGesture { store.switchSession(id: session.id) }
                        .contextMenu {
                            Button("Delete", role: .destructive) {
                                store.deleteSession(id: session.id)
                            }
                        }
                    }
                } header: {
                    Text("SESSIONS")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundColor(.secondary.opacity(0.6))
                        .padding(.leading, -8)
                }
            }
            .listStyle(.sidebar)
            .scrollContentBackground(.hidden)

            Spacer()

            VStack(spacing: 2) {
                Divider().opacity(0.08)
                
                sidebarLink(title: "Chat", icon: "bubble.left.and.bubble.right.fill", target: .chat)
                sidebarLink(title: "Execution History", icon: "clock.fill", target: .history)
                sidebarLink(title: "Memory Bank", icon: "brain.head.profile", target: .memory)
                sidebarLink(title: "Project Workspaces", icon: "folder.fill", target: .workspaces)
                
                // Settings
                Button(action: { showSettings = true }) {
                    HStack {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                        Text("Settings")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.secondary)
                        Spacer()
                        Text("⌘,")
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(.secondary.opacity(0.4))
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                
                Divider().opacity(0.08)
                
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("WORKSPACE")
                            .font(.system(size: 8, weight: .bold, design: .monospaced))
                            .foregroundColor(.secondary.opacity(0.5))
                        Text("Cliently")
                            .font(.system(size: 11, weight: .medium))
                    }
                    Spacer()
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 11))
                        .foregroundColor(.green.opacity(0.6))
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
            }
        }
        .frame(minWidth: 220, idealWidth: 260)
        #if os(macOS)
        .background(BlurView(material: .sidebar, blendingMode: .withinWindow))
        #else
        .background(BlurView())
        #endif
    }

    private func sidebarLink(title: String, icon: String, target: MainView.NeoView) -> some View {
        Button(action: { selectedView = target }) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 11))
                    .foregroundColor(selectedView == target ? .accentColor : .secondary.opacity(0.8))
                Text(title)
                    .font(.system(size: 11, weight: selectedView == target ? .semibold : .medium))
                    .foregroundColor(selectedView == target ? .primary : .secondary)
                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 8)
            .background(selectedView == target ? Color.accentColor.opacity(0.08) : Color.clear)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private func formatDate(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) {
            let df = DateFormatter()
            df.dateStyle = .short
            df.timeStyle = .short
            return df.string(from: d)
        }
        let f2 = ISO8601DateFormatter()
        f2.formatOptions = [.withInternetDateTime]
        if let d = f2.date(from: s) {
            let df = DateFormatter()
            df.dateStyle = .short
            df.timeStyle = .short
            return df.string(from: d)
        }
        return s
    }
}


// MARK: - Context Panel

struct ContextPanelView: View {
    var store: Store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                sectionHeader("GIT", icon: "arrow.triangle.branch")
                VStack(alignment: .leading, spacing: 4) {
                    if !store.branch.isEmpty {
                        HStack(spacing: 4) {
                            Circle().fill(Color.green).frame(width: 5, height: 5)
                            Text(store.branch)
                                .font(.system(size: 11, weight: .medium, design: .monospaced))
                        }
                    }
                    if !store.gitStatus.isEmpty {
                        Text(store.gitStatus)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(.secondary)
                            .lineLimit(8)
                    }
                }
                .padding(.horizontal, 16)

                Divider().opacity(0.08).padding(.horizontal, 12)

                if store.taskActive {
                    sectionHeader("ACTIVE TASK", icon: "bolt.fill")
                    VStack(alignment: .leading, spacing: 6) {
                        Text(store.taskPhase.replacingOccurrences(of: "_", with: " ").capitalized)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(.accentColor)
                    }
                    .padding(.horizontal, 16)
                    Divider().opacity(0.08).padding(.horizontal, 12)
                }

                if !store.timeline.isEmpty {
                    sectionHeader("TIMELINE", icon: "clock")
                    VStack(alignment: .leading, spacing: 6) {
                        ForEach(store.timeline.suffix(8)) { event in
                            HStack(alignment: .top, spacing: 6) {
                                Circle()
                                    .fill(timelineColor(event.event_type))
                                    .frame(width: 5, height: 5)
                                    .padding(.top, 4)
                                VStack(alignment: .leading, spacing: 1) {
                                    Text(event.event_type.capitalized)
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(.secondary)
                                    Text(event.detail)
                                        .font(.system(size: 10))
                                        .foregroundColor(.primary.opacity(0.7))
                                        .lineLimit(2)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 16)
                    Divider().opacity(0.08).padding(.horizontal, 12)
                }

                sectionHeader("RUNTIME", icon: "cpu")
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(store.runtimeConnected ? Color.green : Color.red.opacity(0.6))
                            .frame(width: 6, height: 6)
                        Text(store.runtimeConnected ? "OpenClaw Connected" : "OpenClaw Offline")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(store.runtimeConnected ? .primary : .secondary)
                    }

                    if store.runtimeConnected {
                        if let version = store.runtimeVersion {
                            HStack(spacing: 4) {
                                Text("v\(version)")
                                    .font(.system(size: 9, design: .monospaced))
                                    .foregroundColor(.secondary)
                            }
                        }
                        if store.runtimeActiveTasks > 0 {
                            Text("\(store.runtimeActiveTasks) active task\(store.runtimeActiveTasks == 1 ? "" : "s")")
                                .font(.system(size: 9))
                                .foregroundColor(.orange)
                        }
                    } else {
                        Text(store.runtimeHost)
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(.secondary.opacity(0.5))

                        Button(action: { store.checkRuntimeHealth() }) {
                            Text("Retry Connection")
                                .font(.system(size: 9, weight: .medium))
                        }
                        .buttonStyle(.plain)
                        .foregroundColor(.accentColor)
                    }
                }
                .padding(.horizontal, 16)

                Divider().opacity(0.08).padding(.horizontal, 12)

                sectionHeader("MCPs", icon: "server.rack")
                VStack(alignment: .leading, spacing: 3) {
                    ForEach(store.mcps, id: \.self) { mcp in
                        HStack(spacing: 4) {
                            Circle().fill(Color.green.opacity(0.6)).frame(width: 4, height: 4)
                            Text(mcp)
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(.secondary)
                        }
                    }
                }
                .padding(.horizontal, 16)

                Divider().opacity(0.08).padding(.horizontal, 12)

                sectionHeader("SKILLS", icon: "wrench.and.screwdriver")
                Text("\(store.skills.count) available")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 16)

                Spacer()
            }
            .padding(.top, 16)
        }
        #if os(macOS)
        .background(BlurView(material: .sidebar, blendingMode: .withinWindow).opacity(0.5))
        #else
        .background(BlurView().opacity(0.5))
        #endif
    }

    private func sectionHeader(_ title: String, icon: String) -> some View {
        HStack(spacing: 5) {
            Image(systemName: icon)
                .font(.system(size: 9))
                .foregroundColor(.secondary.opacity(0.5))
            Text(title)
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(.secondary.opacity(0.5))
            Spacer()
        }
        .padding(.horizontal, 16)
    }

    private func timelineColor(_ type: String) -> Color {
        switch type {
        case "plan": return .blue
        case "approve": return .green
        case "reject": return .red
        case "delegate": return .purple
        case "execute": return .orange
        case "review": return .cyan
        case "complete": return .green
        case "error": return .red
        default: return .secondary
        }
    }
}


// MARK: - History View

struct HistoryView: View {
    var store: Store
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Execution History")
                    .font(.system(size: 20, weight: .bold))
                Spacer()
                Button(action: { store.fetchHistory() }) {
                    Image(systemName: "arrow.clockwise")
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            
            if store.history.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "clock.badge.exclamationmark")
                        .font(.system(size: 40))
                        .foregroundColor(.secondary.opacity(0.3))
                    Text("No tasks recorded yet.")
                        .foregroundColor(.secondary)
                }
                .frame(maxHeight: .infinity)
            } else {
                List {
                    ForEach(store.history) { task in
                        HistoryRow(task: task)
                            .padding(.vertical, 8)
                            .listRowInsets(EdgeInsets(top: 0, leading: 24, bottom: 0, trailing: 24))
                    }
                }
                .listStyle(.plain)
            }
        }
    }
}

struct HistoryRow: View {
    let task: TaskHistory
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(task.phase.uppercased())
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(phaseColor(task.phase).opacity(0.15))
                    .foregroundColor(phaseColor(task.phase))
                    .cornerRadius(4)
                
                Spacer()
                
                Text(formatDate(task.created_at))
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }
            
            Text(task.prompt)
                .font(.system(size: 13, weight: .medium))
                .lineLimit(2)
            
            HStack {
                Label(task.id.prefix(8), systemImage: "tag")
                Spacer()
                if task.completed_at != nil {
                    Label("Completed", systemImage: "checkmark.circle.fill")
                        .foregroundColor(.green)
                }
            }
            .font(.system(size: 10))
            .foregroundColor(.secondary.opacity(0.6))
        }
        .padding(16)
        .background(Color.primary.opacity(0.03))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        )
    }
    
    private func phaseColor(_ phase: String) -> Color {
        switch phase {
        case "complete": return .green
        case "failed": return .red
        case "executing": return .orange
        case "planning": return .blue
        default: return .secondary
        }
    }
    
    private func formatDate(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) {
            let df = DateFormatter()
            df.dateStyle = .medium
            df.timeStyle = .short
            return df.string(from: d)
        }
        return s
    }
}


// MARK: - Memory Bank View

struct MemoryBankView: View {
    var store: Store
    @State private var searchText: String = ""
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Memory Bank")
                    .font(.system(size: 20, weight: .bold))
                Spacer()
                
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                    TextField("Search semantic memory...", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.system(size: 13))
                        .onSubmit {
                            store.fetchMemory(query: searchText)
                        }
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Color.primary.opacity(0.05))
                .cornerRadius(8)
                .frame(width: 300)
            }
            .padding(24)
            
            if store.memoryBank.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "brain.head.profile")
                        .font(.system(size: 40))
                        .foregroundColor(.secondary.opacity(0.3))
                    Text("Architectural memory is empty.")
                        .foregroundColor(.secondary)
                }
                .frame(maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(store.memoryBank) { item in
                            MemoryItemRow(item: item)
                        }
                    }
                    .padding(24)
                }
            }
        }
    }
}

struct MemoryItemRow: View {
    let item: MemoryItem
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Knowledge Node", systemImage: "doc.text.fill")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.accentColor)
                Spacer()
                Text(formatDate(item.created_at))
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }
            
            Text(item.content)
                .font(.system(size: 13))
                .lineSpacing(4)
            
            if let metadata = item.metadata, !metadata.isEmpty {
                HStack(spacing: 6) {
                    ForEach(metadata.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        HStack(spacing: 4) {
                            Text(key)
                                .fontWeight(.bold)
                            Text(value)
                        }
                        .font(.system(size: 9, design: .monospaced))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(Color.primary.opacity(0.06))
                        .cornerRadius(4)
                    }
                }
            }
        }
        .padding(16)
        .background(Color.primary.opacity(0.03))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        )
    }
    
    private func formatDate(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) {
            let df = DateFormatter()
            df.dateStyle = .medium
            return df.string(from: d)
        }
        return s
    }
}


// MARK: - Workspaces View

struct WorkspacesView: View {
    var store: Store
    @State private var showAddWorkspace: Bool = false
    @State private var newName: String = ""
    @State private var newPath: String = ""
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Project Workspaces")
                        .font(.system(size: 20, weight: .bold))
                    Text("Neo indexes these projects for architectural context.")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }
                Spacer()
                
                Button(action: { showAddWorkspace = true }) {
                    Label("Add Project", systemImage: "plus")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 7)
                        .background(Color.accentColor)
                        .cornerRadius(8)
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            
            if let status = store.indexingStatus, status.is_indexing {
                indexingProgressBanner(status)
            }
            
            if store.workspaces.isEmpty {
                VStack(spacing: 20) {
                    Image(systemName: "folder.badge.plus")
                        .font(.system(size: 40))
                        .foregroundColor(.secondary.opacity(0.3))
                    Text("No workspaces added yet.")
                        .foregroundColor(.secondary)
                    
                    Button("Add your first project") {
                        showAddWorkspace = true
                    }
                    .buttonStyle(.bordered)
                }
                .frame(maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(store.workspaces) { ws in
                            WorkspaceRow(ws: ws, store: store)
                        }
                    }
                    .padding(24)
                }
            }
        }
        .sheet(isPresented: $showAddWorkspace) {
            addWorkspaceSheet
        }
    }
    
    private func indexingProgressBanner(_ status: IndexingStatus) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "bolt.horizontal.circle.fill")
                    .foregroundColor(.accentColor)
                Text("Indexing Repository Context...")
                    .font(.system(size: 11, weight: .bold))
                Spacer()
                Text("\(status.progress)%")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(.secondary)
            }
            
            ProgressView(value: Double(status.progress), total: 100)
                .progressViewStyle(.linear)
                .tint(.accentColor)
                .controlSize(.small)
            
            Text(status.current_file)
                .font(.system(size: 9, design: .monospaced))
                .foregroundColor(.secondary)
                .lineLimit(1)
        }
        .padding(16)
        .background(Color.accentColor.opacity(0.05))
        .overlay(
            Rectangle().frame(height: 1).foregroundColor(Color.accentColor.opacity(0.1)),
            alignment: .bottom
        )
    }
    
    private var addWorkspaceSheet: some View {
        VStack(spacing: 20) {
            HStack {
                Text("Add Workspace")
                    .font(.headline)
                Spacer()
                Button(action: { showAddWorkspace = false }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            
            VStack(alignment: .leading, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("PROJECT NAME")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.secondary)
                    TextField("e.g. Cliently Neo", text: $newName)
                        .textFieldStyle(.roundedBorder)
                }
                
                VStack(alignment: .leading, spacing: 6) {
                    Text("ABSOLUTE PATH")
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(.secondary)
                    TextField("/Users/albin/Documents/project", text: $newPath)
                        .textFieldStyle(.roundedBorder)
                    Text("Ensure Neo has read access to this directory.")
                        .font(.system(size: 9))
                        .foregroundColor(.secondary.opacity(0.6))
                }
            }
            
            Spacer()
            
            Button(action: {
                store.addWorkspace(name: newName, path: newPath)
                newName = ""
                newPath = ""
                showAddWorkspace = false
            }) {
                Text("Add Workspace")
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(Color.accentColor)
                    .cornerRadius(8)
            }
            .buttonStyle(.plain)
            .disabled(newName.isEmpty || newPath.isEmpty)
        }
        .padding(24)
        .frame(width: 400, height: 320)
    }
}

struct WorkspaceRow: View {
    let ws: WorkspacePayload
    var store: Store
    @State private var isHovered = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 8) {
                        Text(ws.name)
                            .font(.system(size: 14, weight: .bold))
                        
                        if ws.is_indexed {
                            Text("INDEXED")
                                .font(.system(size: 8, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.green.opacity(0.15))
                                .foregroundColor(.green)
                                .cornerRadius(4)
                        } else {
                            Text("PENDING")
                                .font(.system(size: 8, weight: .bold))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.orange.opacity(0.15))
                                .foregroundColor(.orange)
                                .cornerRadius(4)
                        }
                    }
                    
                    HStack(spacing: 4) {
                        Image(systemName: "folder")
                            .font(.system(size: 10))
                        Text(ws.path)
                            .font(.system(size: 11, design: .monospaced))
                    }
                    .foregroundColor(.secondary)
                }
                
                Spacer()
                
                HStack(spacing: 12) {
                    if let status = store.indexingStatus, status.is_indexing {
                        ProgressView().controlSize(.small)
                    } else {
                        Button(action: { store.indexWorkspace(id: ws.id) }) {
                            Image(systemName: "bolt.fill")
                                .font(.system(size: 12))
                                .foregroundColor(.accentColor)
                        }
                        .buttonStyle(.plain)
                        .help("Re-index Architecture")
                    }
                    
                    Button(action: { store.deleteWorkspace(id: ws.id) }) {
                        Image(systemName: "trash")
                            .font(.system(size: 11))
                            .foregroundColor(.red.opacity(0.6))
                    }
                    .buttonStyle(.plain)
                }
            }
            
            if let last = ws.last_indexed {
                HStack {
                    Text("Last indexed: \(formatDate(last))")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary.opacity(0.6))
                    Spacer()
                }
            }
        }
        .padding(16)
        .background(Color.primary.opacity(isHovered ? 0.05 : 0.03))
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        )
        .onHover { h in isHovered = h }
    }
    
    private func formatDate(_ s: String) -> String {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) {
            let df = DateFormatter()
            df.dateStyle = .medium
            df.timeStyle = .short
            return df.string(from: d)
        }
        return s
    }
}


// MARK: - Message Bubble

struct MessageBubbleView: View {
    let message: MessagePayload
    var store: Store
    @State private var isHovered: Bool = false
    @State private var copied: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            if message.isUser {
                userBubble
            } else if let card = message.approvalCard {
                approvalCardView(card)
            } else {
                neoBubble
            }
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 4)
    }

    private var userBubble: some View {
        HStack {
            Spacer(minLength: 120)
            VStack(alignment: .trailing, spacing: 4) {
                MarkdownContentView(content: message.content, isUser: true)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 11)
                    .background(
                        LinearGradient(
                            gradient: Gradient(colors: [Color.accentColor, Color.accentColor.opacity(0.85)]),
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .foregroundColor(.white)
                    .cornerRadius(18)
                    .shadow(color: Color.accentColor.opacity(0.2), radius: 5, y: 2)

                if message.source == "telegram" {
                    HStack(spacing: 4) {
                        Image(systemName: "paperplane.fill")
                            .font(.system(size: 7))
                        Text("Sent via Telegram")
                            .font(.system(size: 8, weight: .bold))
                    }
                    .foregroundColor(.secondary.opacity(0.6))
                    .padding(.trailing, 4)
                }
            }
        }
    }

    private var neoBubble: some View {
        HStack(alignment: .top, spacing: 12) {
            ZStack {
                Circle()
                    .fill(LinearGradient(colors: [Color.accentColor.opacity(0.1), Color.accentColor.opacity(0.05)], startPoint: .topLeading, endPoint: .bottomTrailing))
                    .frame(width: 28, height: 28)
                Image(systemName: "cpu.fill")
                    .font(.system(size: 14))
                    .foregroundColor(.accentColor)
            }
            .padding(.top, 4)

            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(message.displayRole.uppercased())
                        .font(.system(size: 10, weight: .black))
                        .foregroundColor(.accentColor.opacity(0.8))
                    Spacer()
                    if isHovered || copied {
                        Button(action: copyText) {
                            HStack(spacing: 4) {
                                if copied { Text("COPIED").font(.system(size: 8, weight: .bold)) }
                                Image(systemName: copied ? "checkmark" : "doc.on.doc")
                            }
                            .font(.system(size: 10))
                            .foregroundColor(copied ? .green : .secondary.opacity(0.6))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.primary.opacity(0.05))
                            .cornerRadius(4)
                        }
                        .buttonStyle(.plain)
                        .transition(.opacity)
                    }
                }
                
                MarkdownContentView(content: message.content)
                    .font(.system(size: 13))
                    .lineSpacing(4)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(NeoTheme.surface)
            .cornerRadius(18)
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .stroke(NeoTheme.border, lineWidth: 1)
            )
            
            Spacer(minLength: 50)
        }
        .onHover { h in
            withAnimation(.easeInOut(duration: 0.1)) { isHovered = h }
        }
    }

    private func approvalCardView(_ card: ApprovalCard) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "shield.checkered")
                    .foregroundColor(.orange)
                    .font(.system(size: 12))
                Text("Approval Required")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(.orange)
                Spacer()
            }
            MarkdownContentView(content: card.plan)
                .font(.system(size: 12, design: .monospaced))
                .lineSpacing(3)
                .foregroundColor(.primary.opacity(0.8))
                .lineLimit(nil)
                .padding(10)
                .background(Color.primary.opacity(0.04))
                .cornerRadius(8)
                
            HStack(spacing: 10) {
                Button(action: { store.approveTask() }) {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark")
                        Text("Approve")
                    }
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 7)
                    .background(Color.green)
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)

                Button(action: { /* Focus input field conceptually */ }) {
                    HStack(spacing: 4) {
                        Image(systemName: "pencil")
                        Text("Modify")
                    }
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.primary.opacity(0.8))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 7)
                    .background(Color.primary.opacity(0.08))
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)

                Button(action: { store.rejectTask() }) {
                    HStack(spacing: 4) {
                        Image(systemName: "xmark")
                        Text("Reject")
                    }
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(.red)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 7)
                    .background(Color.red.opacity(0.1))
                    .cornerRadius(8)
                }
                .buttonStyle(.plain)

                Spacer()
            }
        }
        .padding(16)
        .background(Color.orange.opacity(0.06))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(Color.orange.opacity(0.2), lineWidth: 1)
        )
        .cornerRadius(12)
    }

    private func copyText() {
        #if os(macOS)
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(message.content, forType: .string)
        #else
        UIPasteboard.general.string = message.content
        #endif
        withAnimation { copied = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation { copied = false }
        }
    }
}

// MARK: - Settings View

struct SettingsView: View {
    var store: Store
    @Binding var isPresented: Bool
    @AppStorage("serverURL") private var serverURL: String = "http://127.0.0.1:8080"

    var body: some View {
        VStack(spacing: 20) {
            HStack {
                Text("Neo Settings")
                    .font(.headline)
                Spacer()
                Button(action: { isPresented = false }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Daemon Server URL")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                TextField("http://127.0.0.1:8080", text: $serverURL)
                    .textFieldStyle(.roundedBorder)
                    #if os(iOS)
                    .keyboardType(.URL)
                    .autocapitalization(.none)
                    #endif
                
                Text("Use Ngrok or Tailscale for remote iOS access.")
                    .font(.caption)
                    .foregroundColor(.secondary.opacity(0.8))
            }

            Spacer()
            
            HStack {
                Spacer()
                Button("Save & Reconnect") {
                    store.connect()
                    isPresented = false
                }
                #if os(macOS)
                .buttonStyle(.borderedProminent)
                #else
                .buttonStyle(.bordered)
                .tint(.blue)
                #endif
            }
        }
        .padding(20)
        .frame(width: 350, height: 200)
    }
}

