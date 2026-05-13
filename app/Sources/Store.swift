import SwiftUI
import Combine

// MARK: - API Models

struct HealthResponse: Decodable {
    let status: String
    let service: String
    let ai_ready: Bool
    let branch: String?
    let runtime: RuntimePayload?
}

struct RuntimePayload: Decodable {
    let status: String
    let host: String?
    let last_check: String?
    let version: String?
    let sandbox_active: Bool?
    let active_tasks: Int?
    let error: String?

    var isConnected: Bool { status == "connected" }
}

struct SessionPayload: Identifiable, Decodable {
    let id: String
    let title: String
    let model: String
    let telegram_chat_id: String?
    let created_at: String
    let updated_at: String
    
    var isTelegram: Bool {
        telegram_chat_id != nil || id.hasPrefix("-")
    }
}

struct WorkspacePayload: Identifiable, Decodable {
    let id: String
    let name: String
    let path: String
    let is_indexed: Bool
    let last_indexed: String?
    let created_at: String
}

struct IndexingStatus: Decodable {
    let is_indexing: Bool
    let progress: Int
    let current_file: String
    let total_files: Int
}

struct MessagePayload: Identifiable, Decodable {
    let id: Int
    let session_id: String
    let role: String
    let content: String
    let metadata_json: String?
    let created_at: String

    var isUser: Bool { role == "albin" }

    var displayRole: String {
        if role == "albin" { return "Albin" }
        if role == "neo" { return "Neo" }
        return role.capitalized
    }

    var source: String? {
        guard let json = metadata_json,
              let data = json.data(using: .utf8),
              let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return nil }
        return dict["source"] as? String
    }

    var approvalCard: ApprovalCard? {
        guard let json = metadata_json,
              let data = json.data(using: .utf8),
              let decoded = try? JSONDecoder().decode(ApprovalCard.self, from: data),
              decoded.type == "approval_card"
        else { return nil }
        return decoded
    }
}

struct ApprovalCard: Decodable {
    let type: String
    let task_id: String
    let plan: String
}

struct ChatResponsePayload: Decodable {
    let response: String
    let task_id: String?
    let task_phase: String?
}

struct TaskStatusPayload: Decodable {
    let active: Bool
    let phase: String
    let task_id: String?
}

struct TimelineEvent: Identifiable, Decodable {
    let event_type: String
    let agent_role: String?
    let detail: String
    let timestamp: String

    var id: String { "\(timestamp)-\(event_type)-\(detail.prefix(20))" }
}

struct ContextPayload: Decodable {
    let workspace: String
    let skills: [String]
    let mcps: [String]
    let branch: String
    let git_status: String
    let runtime: RuntimePayload?
}

struct WSMessage: Decodable {
    let type: String
    let phase: String?
    let role: String?
    let content: String?
    let agent: String?
    let status: String?
    let task_id: String?
    let plan: String?
    let connected: Bool?
    let task_ref: String?
    let elapsed: Int?
}


struct TaskHistory: Identifiable, Decodable {
    let id: String
    let session_id: String
    let prompt: String
    let phase: String
    let created_at: String
    let completed_at: String?
}

struct MemoryItem: Identifiable, Decodable {
    let id: String
    let content: String
    let metadata: [String: String]?
    let created_at: String
}

// MARK: - Store

@Observable
class Store {
    var isConnected: Bool = false
    var aiReady: Bool = false
    var branch: String = ""

    var sessions: [SessionPayload] = []
    var activeSessionId: String? = nil

    var messages: [MessagePayload] = []
    var isProcessing: Bool = false

    var activeTaskId: String? = nil
    var taskPhase: String = "idle"

    var skills: [String] = []
    var mcps: [String] = []
    var gitStatus: String = ""
    var timeline: [TimelineEvent] = []

    var history: [TaskHistory] = []
    var memoryBank: [MemoryItem] = []
    
    var workspaces: [WorkspacePayload] = []
    var indexingStatus: IndexingStatus? = nil

    // OpenClaw Runtime
    var runtimeConnected: Bool = false
    var runtimeVersion: String? = nil
    var runtimeHost: String = "localhost:9090"
    var runtimeError: String? = nil
    var runtimeActiveTasks: Int = 0

    var selectedModel: String = "gemini-2.5-flash"

    private var wsTask: URLSessionWebSocketTask? = nil

    var taskActive: Bool {
        !["idle", "complete", "failed", "rejected"].contains(taskPhase)
    }

    var inputLocked: Bool {
        isProcessing || activeSessionId == nil || (taskActive && taskPhase != "awaiting_approval")
    }

    var taskStatusText: String {
        switch taskPhase {
        case "planning": return "Strategic planning..."
        case "awaiting_approval": return "Awaiting your approval"
        case "delegating": return "Dispatching agents..."
        case "executing": return "Agents executing..."
        case "reviewing": return "Reviewing output..."
        case "complete": return "Complete"
        case "failed": return "Failed"
        case "rejected": return "Rejected"
        default: return ""
        }
    }

    // MARK: - Connection

    func connect() {
        checkHealth()
        fetchSessions()
        fetchContext()
        fetchHistory()
        fetchMemory()
        fetchWorkspaces()
    }

    private func checkHealth() {
        apiGet("health") { (resp: HealthResponse) in
            self.isConnected = resp.status == "ok"
            self.aiReady = resp.ai_ready
            self.branch = resp.branch ?? ""
            if let rt = resp.runtime {
                self.updateRuntime(rt)
            }
        }
    }

    func checkRuntimeHealth() {
        apiGet("runtime/health") { (rt: RuntimePayload) in
            self.updateRuntime(rt)
        }
    }

    private func updateRuntime(_ rt: RuntimePayload) {
        runtimeConnected = rt.isConnected
        runtimeVersion = rt.version
        runtimeHost = rt.host ?? "localhost:9090"
        runtimeError = rt.error
        runtimeActiveTasks = rt.active_tasks ?? 0
    }

    // MARK: - Sessions

    func fetchSessions() {
        apiGet("sessions") { (sessions: [SessionPayload]) in
            self.sessions = sessions
            if self.activeSessionId == nil {
                if let first = sessions.first {
                    self.switchSession(id: first.id)
                } else {
                    self.createSession()
                }
            }
        }
    }

    func createSession() {
        apiPost("sessions?model=\(selectedModel)", body: nil as String?) { (session: SessionPayload) in
            self.sessions.insert(session, at: 0)
            self.switchSession(id: session.id)
        }
    }

    func switchSession(id: String) {
        disconnectWS()
        activeSessionId = id
        messages = []
        activeTaskId = nil
        taskPhase = "idle"
        timeline = []
        fetchMessages()
        fetchTaskStatus()
        connectWS(sessionId: id)
    }

    func deleteSession(id: String) {
        apiDelete("sessions/\(id)") {
            self.sessions.removeAll { $0.id == id }
            if self.activeSessionId == id {
                self.activeSessionId = nil
                self.messages = []
                if let next = self.sessions.first {
                    self.switchSession(id: next.id)
                }
            }
        }
    }

    // MARK: - Messages

    func fetchMessages() {
        guard let sid = activeSessionId else { return }
        apiGet("sessions/\(sid)/messages") { (msgs: [MessagePayload]) in
            self.messages = msgs
        }
    }

    // MARK: - Chat

    func send(_ prompt: String) {
        let trimmed = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !inputLocked else { return }
        guard let sid = activeSessionId else { return }

        let localMsg = MessagePayload(
            id: Int.random(in: 100000...999999),
            session_id: sid, role: "albin", content: trimmed,
            metadata_json: nil, created_at: ISO8601DateFormatter().string(from: Date())
        )
        messages.append(localMsg)
        isProcessing = true

        struct ChatBody: Encodable {
            let session_id: String
            let prompt: String
            let model: String
        }

        let body = ChatBody(session_id: sid, prompt: trimmed, model: selectedModel)

        apiPost("chat", body: body) { (resp: ChatResponsePayload) in
            self.isProcessing = false
            let neoMsg = MessagePayload(
                id: Int.random(in: 100000...999999),
                session_id: sid, role: "neo", content: resp.response,
                metadata_json: nil, created_at: ISO8601DateFormatter().string(from: Date())
            )
            self.messages.append(neoMsg)
            if let tid = resp.task_id {
                self.activeTaskId = tid
                self.taskPhase = resp.task_phase ?? "planning"
            }
            self.fetchSessions()
        } onError: {
            self.isProcessing = false
        }
    }

    // MARK: - Task Actions

    func approveTask() {
        guard let tid = activeTaskId else { return }
        struct Body: Encodable { let task_id: String }
        apiPost("task/approve", body: Body(task_id: tid)) { (_: [String: Bool]) in }
    }

    func rejectTask() {
        guard let tid = activeTaskId else { return }
        struct Body: Encodable { let task_id: String }
        apiPost("task/reject", body: Body(task_id: tid)) { (_: [String: Bool]) in
            self.taskPhase = "rejected"
            self.activeTaskId = nil
        }
    }

    func fetchTaskStatus() {
        guard let sid = activeSessionId else { return }
        apiGet("task/status?session_id=\(sid)") { (status: TaskStatusPayload) in
            self.taskPhase = status.phase
            self.activeTaskId = status.task_id
            if let tid = status.task_id, status.active {
                self.fetchTimeline(taskId: tid)
            }
        }
    }

    func fetchTimeline(taskId: String) {
        apiGet("task/\(taskId)/timeline") { (events: [TimelineEvent]) in
            self.timeline = events
        }
    }

    // MARK: - Context

    func fetchContext() {
        apiGet("context") { (ctx: ContextPayload) in
            self.skills = ctx.skills
            self.mcps = ctx.mcps
            self.gitStatus = ctx.git_status
            self.branch = ctx.branch
            if let rt = ctx.runtime {
                self.updateRuntime(rt)
            }
        }
    }

    // MARK: - History & Memory

    func fetchHistory() {
        apiGet("tasks") { (tasks: [TaskHistory]) in
            self.history = tasks
        }
    }

    func fetchMemory(query: String? = nil) {
        var path = "memory"
        if let q = query, !q.isEmpty {
            if let encoded = q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) {
                path += "?q=\(encoded)"
            }
        }
        apiGet(path) { (memory: [MemoryItem]) in
            self.memoryBank = memory
        }
    }

    // MARK: - Workspaces

    func fetchWorkspaces() {
        apiGet("workspaces") { (ws: [WorkspacePayload]) in
            self.workspaces = ws
        }
    }

    func addWorkspace(name: String, path: String) {
        struct Body: Encodable { let name: String; let path: String }
        apiPost("workspaces", body: Body(name: name, path: path)) { (ws: WorkspacePayload) in
            self.workspaces.insert(ws, at: 0)
        }
    }

    func deleteWorkspace(id: String) {
        apiDelete("workspaces/\(id)") {
            self.workspaces.removeAll { $0.id == id }
        }
    }

    func indexWorkspace(id: String) {
        apiPost("workspaces/\(id)/index", body: nil as String?) { (_: [String: String]) in
            self.pollIndexingStatus()
        }
    }

    func pollIndexingStatus() {
        apiGet("workspaces/index/status") { (status: IndexingStatus) in
            self.indexingStatus = status
            if status.is_indexing {
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    self.pollIndexingStatus()
                }
            } else {
                self.fetchWorkspaces()
            }
        }
    }

    // MARK: - WebSocket

    private func connectWS(sessionId: String) {
        guard let url = URL(string: "\(wsBase)/ws/\(sessionId)") else { return }
        wsTask = URLSession.shared.webSocketTask(with: url)
        wsTask?.resume()
        receiveWS()
    }

    private func disconnectWS() {
        wsTask?.cancel(with: .goingAway, reason: nil)
        wsTask = nil
    }

    private func receiveWS() {
        wsTask?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    if let data = text.data(using: .utf8),
                       let msg = try? JSONDecoder().decode(WSMessage.self, from: data) {
                        DispatchQueue.main.async { self.handleWSMessage(msg) }
                    }
                default: break
                }
                self.receiveWS()
            case .failure:
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    if let sid = self.activeSessionId { self.connectWS(sessionId: sid) }
                }
            }
        }
    }

    private func handleWSMessage(_ msg: WSMessage) {
        switch msg.type {
        case "phase":
            taskPhase = msg.phase ?? taskPhase
            if ["complete", "failed", "rejected"].contains(taskPhase) {
                fetchMessages()
                activeTaskId = nil
            }
        case "message":
            if let content = msg.content, let role = msg.role, let sid = activeSessionId {
                let m = MessagePayload(
                    id: Int.random(in: 100000...999999),
                    session_id: sid, role: role, content: content,
                    metadata_json: nil, created_at: ISO8601DateFormatter().string(from: Date())
                )
                messages.append(m)
            }
        case "approval_request":
            taskPhase = "awaiting_approval"
            if let tid = msg.task_id { activeTaskId = tid }
            fetchMessages()
        case "agent_status":
            if let tid = activeTaskId { fetchTimeline(taskId: tid) }
        case "runtime_status":
            if let connected = msg.connected { runtimeConnected = connected }
        case "openclaw_progress":
            // Could update a progress indicator
            break
        default: break
        }
    }

    // MARK: - Networking

    var base: String {
        let defaultURL = "http://127.0.0.1:8080"
        let saved = UserDefaults.standard.string(forKey: "serverURL") ?? defaultURL
        return saved.isEmpty ? defaultURL : saved
    }
    
    var wsBase: String {
        let b = base
        if b.starts(with: "https://") {
            return b.replacingOccurrences(of: "https://", with: "wss://")
        } else if b.starts(with: "http://") {
            return b.replacingOccurrences(of: "http://", with: "ws://")
        }
        return "ws://\(b)"
    }

    private func apiGet<T: Decodable>(_ path: String, onSuccess: @escaping (T) -> Void) {
        guard let url = URL(string: "\(base)/\(path)") else { return }
        URLSession.shared.dataTask(with: url) { data, _, error in
            guard let data = data, error == nil,
                  let decoded = try? JSONDecoder().decode(T.self, from: data)
            else { return }
            DispatchQueue.main.async { onSuccess(decoded) }
        }.resume()
    }

    private func apiPost<B: Encodable, T: Decodable>(
        _ path: String, body: B?,
        onSuccess: @escaping (T) -> Void,
        onError: (() -> Void)? = nil
    ) {
        guard let url = URL(string: "\(base)/\(path)") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.timeoutInterval = 120
        if let body = body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try? JSONEncoder().encode(body)
        }
        URLSession.shared.dataTask(with: req) { data, _, error in
            DispatchQueue.main.async {
                if error != nil { onError?(); return }
                guard let data = data,
                      let decoded = try? JSONDecoder().decode(T.self, from: data)
                else { onError?(); return }
                onSuccess(decoded)
            }
        }.resume()
    }

    private func apiDelete(_ path: String, onSuccess: @escaping () -> Void) {
        guard let url = URL(string: "\(base)/\(path)") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "DELETE"
        URLSession.shared.dataTask(with: req) { _, _, _ in
            DispatchQueue.main.async { onSuccess() }
        }.resume()
    }
}
