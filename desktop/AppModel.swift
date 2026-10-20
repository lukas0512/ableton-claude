import SwiftUI
import AppKit
import UniformTypeIdentifiers

@MainActor
final class AppModel: ObservableObject {
    @Published var snapshot: [String: Any] = [:]
    @Published var selectedFolder = ""
    @Published var userLibrary = ""
    @Published var genreName = ""
    @Published var referenceFiles: [String] = []
    @Published var preview: [String: Any] = [:]
    @Published var message = ""
    @Published var error = ""
    @Published var ready = false
    @Published var loaded = false
    @Published var busy = false
    @Published var step = 0
    @Published var onboardingComplete = false
    @Published var route = "studio"
    @Published var activeGenre = ""
    @Published var assistant = ""
    let provider = "chatgpt"
    @Published var modelID = ""
    @Published var showPlanWelcome = false
    @Published var models: [[String: String]] = []
    @Published var draft = ""
    @Published var report: [String: Any] = [:]
    @Published var reportFile = ""
    @Published var selectedTrack: [String: Any] = [:]
    @Published var renderStart = "1"
    @Published var renderEnd = "33"
    private var process: Process?
    private let input = Pipe()
    private let output = Pipe()
    private var buffer = Data()
    private var counter = 0
    private var pending: [Int: ([String: Any]) -> Void] = [:]
    private var timeouts: [Int: DispatchWorkItem] = [:]
    private var timer: Timer?
    private var refreshing = false

    var job: [String: Any] { snapshot["job"] as? [String: Any] ?? [:] }
    var genres: [[String: Any]] { snapshot["genres"] as? [[String: Any]] ?? [] }
    var bridge: [String: Any] { snapshot["bridge"] as? [String: Any] ?? [:] }
    var song: [String: Any] { bridge["song"] as? [String: Any] ?? [:] }
    var tracks: [[String: Any]] { song["tracks"] as? [[String: Any]] ?? [] }
    var connection: [String: Any] { snapshot["connection"] as? [String: Any] ?? [:] }
    var chat: [String: Any] { snapshot["chat"] as? [String: Any] ?? [:] }
    var production: [String: Any] { snapshot["production"] as? [String: Any] ?? [:] }
    var hasProduction: Bool { production["active"] as? Bool == true }
    var existingProduction: Bool { hasProduction && production["mode"] as? String == "existing" }
    var guidedProduction: Bool { hasProduction && !existingProduction }
    var productionProjects: [[String: Any]] { snapshot["production_projects"] as? [[String: Any]] ?? [] }
    var productionStage: String { production["stage"] as? String ?? "loop" }
    var productionNeedsResume: Bool { production["needs_resume"] as? Bool == true }
    var productionLabel: String { ["loop": "Loop", "groove": "Groove", "arrangement": "Arranjo"][productionStage] ?? "Loop" }
    var chatMessages: [[String: Any]] { chat["messages"] as? [[String: Any]] ?? [] }
    var proposals: [[String: Any]] { chat["pending"] as? [[String: Any]] ?? [] }
    var render: [String: Any] { snapshot["render"] as? [String: Any] ?? [:] }
    var connected: Bool { bridge["connected"] as? Bool ?? false }
    var mcpReady: Bool { connection["state"] as? String == "ready" }
    var training: Bool { ["running", "queued"].contains(job["state"] as? String ?? "") }
    var chatRunning: Bool { chat["state"] as? String == "running" }
    var rendering: Bool { ["recording", "finalizing"].contains(render["state"] as? String ?? "") }
    var auth: [String: Any] { snapshot["auth"] as? [String: Any] ?? [:] }
    var accountConnected: Bool { auth["connected"] as? Bool ?? false }
    var awaitingLogin: Bool { auth["awaiting_login"] as? Bool ?? false }
    var accountID: String { (auth["account"] as? [String: Any])?["id"] as? String ?? "" }
    var accountEmail: String { (auth["account"] as? [String: Any])?["email"] as? String ?? "" }
    var modelAvailable: Bool { models.contains(where: { $0["id"] == modelID }) }
    var canChat: Bool { hasProduction && connected && ready && mcpReady && accountConnected && modelAvailable && !awaitingLogin && !chatRunning && !busy && proposals.isEmpty && !productionNeedsResume }
    var claude: [String: Any] { snapshot["claude"] as? [String: Any] ?? [:] }
    var claudeInstalled: Bool { claude["installed"] as? Bool ?? false }
    var claudeConfigured: Bool { claude["configured"] as? Bool ?? false }
    var settings: [String: Any] { snapshot["settings"] as? [String: Any] ?? [:] }
    var sampleCount: Int { settings["sample_count"] as? Int ?? 0 }
    var sampleFolders: [String] { settings["sample_folders"] as? [String] ?? [] }
    var chatgptReady: Bool { accountConnected && modelAvailable }
    var aiReady: Bool { assistant == "claude" ? claudeConfigured : assistant == "chatgpt" && chatgptReady }
    static let lastStep = 5
    var dataDirectory: String { snapshot["data_dir"] as? String ?? NSHomeDirectory() + "/Music/Ableton Claude" }
    var canContinue: Bool {
        switch step {
        case 1: return connected && mcpReady
        case 2: return !busy
        case 3: return aiReady && !busy
        case 4: return !training && !busy
        case 5: return connected && mcpReady && aiReady && !busy
        default: return loaded
        }
    }
    var trainingStage: String {
        if job["state"] as? String == "queued" { return "Aguardando outra análise terminar" }
        if job["state"] as? String == "done" { return "Seu perfil musical está pronto" }
        if job["state"] as? String == "partial" { return "Perfis salvos; algumas referências precisam de atenção" }
        if job["state"] as? String == "failed" { return "Não foi possível concluir o aprendizado" }
        let log = (job["log"] as? [String] ?? []).joined(separator: " ")
        if log.contains("listening") { return "Ouvindo instrumentos e aprendendo o arranjo" }
        if log.contains("element timbre") { return "Aprendendo os timbres de cada elemento" }
        if log.contains("fingerprints") { return "Aprendendo groove, harmonia e dinâmica" }
        return "Medindo ritmo, tonalidade e equilíbrio do áudio"
    }

    init() { start() }

    func start() {
        guard let resources = Bundle.main.resourceURL else { error = "Os recursos do app não foram encontrados."; return }
        let task = Process()
        task.executableURL = resources.appendingPathComponent("backend/ableton-claude-backend")
        task.arguments = ["--desktop"]
        task.standardInput = input
        task.standardOutput = output
        let data = ProcessInfo.processInfo.environment["ABLETON_CLAUDE_DATA"] ?? NSHomeDirectory() + "/Music/Ableton Claude"
        let logs = URL(fileURLWithPath: data).appendingPathComponent("Logs")
        try? FileManager.default.createDirectory(at: logs, withIntermediateDirectories: true)
        let log = logs.appendingPathComponent("app.log")
        if !FileManager.default.fileExists(atPath: log.path) { _ = FileManager.default.createFile(atPath: log.path, contents: nil) }
        if let handle = try? FileHandle(forWritingTo: log) { handle.seekToEndOfFile(); task.standardError = handle }
        output.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            Task { @MainActor in self.receive(data) }
        }
        task.terminationHandler = { task in
            Task { @MainActor in
                self.ready = false; self.busy = false; self.refreshing = false
                self.error = "O serviço local encerrou. Consulte o log nos seus dados e abra o app novamente."
                let callbacks = self.pending.values
                self.pending.removeAll()
                callbacks.forEach { $0(["error": self.error]) }
            }
        }
        do {
            try task.run()
            process = task; ready = true
            refresh()
            timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { _ in Task { @MainActor in self.refresh() } }
        } catch { self.error = "Não foi possível iniciar o serviço: \(error.localizedDescription)" }
    }

    func receive(_ data: Data) {
        buffer.append(data)
        while let newline = buffer.firstIndex(of: 10) {
            let line = buffer.prefix(upTo: newline)
            buffer.removeSubrange(...newline)
            if let value = try? JSONSerialization.jsonObject(with: line) as? [String: Any], let id = value["id"] as? Int {
                timeouts.removeValue(forKey: id)?.cancel()
                pending.removeValue(forKey: id)?(value)
            }
        }
    }

    func request(_ method: String, params: [String: Any] = [:], timeout: Double = 35,
                 completion: @escaping ([String: Any]) -> Void) {
        guard ready else { completion(["error": "O serviço local ainda não está pronto."]); return }
        counter += 1
        let id = counter
        do {
            var data = try JSONSerialization.data(withJSONObject: ["id": id, "method": method, "params": params])
            data.append(10)
            pending[id] = completion
            let expiry = DispatchWorkItem {
                Task { @MainActor in
                    self.timeouts.removeValue(forKey: id)
                    self.pending.removeValue(forKey: id)?(["error": "Esta operação demorou demais. Verifique a conexão antes de repetir."])
                }
            }
            timeouts[id] = expiry
            DispatchQueue.main.asyncAfter(deadline: .now() + timeout, execute: expiry)
            try input.fileHandleForWriting.write(contentsOf: data)
        } catch {
            timeouts.removeValue(forKey: id)?.cancel()
            pending.removeValue(forKey: id)
            completion(["error": error.localizedDescription])
        }
    }

    func refresh() {
        guard ready && !refreshing else { return }
        refreshing = true
        request("snapshot", params: ["folder": selectedFolder]) { value in
            self.refreshing = false
            if let result = value["result"] as? [String: Any] {
                self.snapshot = result
                if self.userLibrary.isEmpty { self.userLibrary = result["user_library"] as? String ?? "" }
                if self.selectedFolder.isEmpty { self.selectedFolder = result["last_folder"] as? String ?? "" }
                if !self.loaded {
                    let settings = result["settings"] as? [String: Any] ?? [:]
                    self.step = min(AppModel.lastStep, max(0, settings["onboarding_step"] as? Int ?? 0))
                    self.onboardingComplete = settings["onboarding_complete"] as? Bool ?? false
                    self.activeGenre = settings["active_genre"] as? String ?? ""
                    self.assistant = settings["assistant"] as? String ?? ""
                    self.modelID = settings["model"] as? String ?? ""
                    self.loaded = true
                }
                self.models = self.auth["models"] as? [[String: String]] ?? []
                if !self.models.isEmpty && !self.models.contains(where: { $0["id"] == self.modelID }) {
                    self.modelID = self.models.first?["id"] ?? ""
                    self.savePreferences(["provider": self.provider, "model": self.modelID])
                }
                if self.accountConnected && self.auth["welcome_seen"] as? Bool != true { self.showPlanWelcome = true }
                if self.activeGenre.isEmpty { self.activeGenre = self.genres.first?["genre"] as? String ?? "" }
            } else if let error = value["error"] as? String { self.error = error }
        }
    }

    func perform(_ method: String, params: [String: Any] = [:], timeout: Double = 35,
                 completion: (([String: Any]) -> Void)? = nil) {
        busy = true; error = ""; message = ""
        request(method, params: params, timeout: timeout) { value in
            self.busy = false
            if let error = value["error"] as? String { self.error = error }
            if let result = value["result"] as? [String: Any] {
                if let message = result["message"] as? String { self.message = message }
                completion?(result)
            }
            self.refresh()
        }
    }

    func savePreferences(_ values: [String: Any]) {
        request("save_settings", params: values) { value in
            if let error = value["error"] as? String { self.error = error }
        }
    }
    func advance() {
        if step < AppModel.lastStep { step += 1; savePreferences(["onboarding_step": step]) }
        else {
            onboardingComplete = true; route = "studio"
            savePreferences(["onboarding_complete": true, "onboarding_step": AppModel.lastStep, "assistant": assistant,
                             "provider": provider, "model": modelID, "active_genre": activeGenre])
        }
        error = ""; message = ""
    }
    func back() { step = max(0, step - 1); savePreferences(["onboarding_step": step]); error = "" }

    func chooseFolder(library: Bool = false) {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false
        panel.prompt = library ? "Selecionar biblioteca" : "Selecionar referências"
        panel.message = library ? "Escolha a User Library configurada no Ableton." : "Esta pasta deve conter uma subpasta para cada gênero."
        if panel.runModal() == .OK, let url = panel.url {
            if library { userLibrary = url.path }
            else {
                selectedFolder = url.path
                perform("preview_genres", params: ["folder": selectedFolder]) { self.preview = $0 }
            }
        }
    }
    func chooseReferences() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = false; panel.canChooseFiles = true
        panel.allowsMultipleSelection = true; panel.allowedContentTypes = [.audio]
        panel.prompt = "Adicionar referências"
        panel.message = "Escolha as faixas que representam o gênero. Três a cinco referências são um bom começo."
        if panel.runModal() == .OK { referenceFiles = Array(Set(referenceFiles + panel.urls.map(\.path))).sorted(); preview = [:] }
    }
    func train() {
        if !preview.isEmpty, let folder = preview["folder"] as? String {
            selectedFolder = folder
            startTraining()
        } else {
            perform("prepare_genre", params: ["name": genreName, "files": referenceFiles]) { result in
                self.preview = result
                self.selectedFolder = result["folder"] as? String ?? ""
                self.startTraining()
            }
        }
    }
    private func startTraining() {
        perform("learn", params: ["folder": selectedFolder]) { result in
            self.snapshot["job"] = result
            self.message = "Aprendizado iniciado. Você pode acompanhar as etapas nesta tela."
        }
    }
    func installBridge() { perform("install_bridge", params: ["library": userLibrary]) }
    func chooseAssistant(_ name: String) { assistant = name; savePreferences(["assistant": name]); error = "" }
    func configureClaude() { perform("configure_claude") { _ in self.refresh() } }
    func openClaude() { restartClaude(quitFirst: false) }
    func restartClaude() { restartClaude(quitFirst: true) }
    private func restartClaude(quitFirst: Bool) {
        let running = quitFirst ? NSRunningApplication.runningApplications(withBundleIdentifier: "com.anthropic.claudefordesktop") : []
        running.forEach { $0.terminate() }
        let paths = ["/Applications/Claude.app", NSHomeDirectory() + "/Applications/Claude.app"]
        guard let path = paths.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
            NSWorkspace.shared.open(URL(string: "https://claude.ai/download")!); return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + (running.isEmpty ? 0 : 2.5)) {
            NSWorkspace.shared.openApplication(at: URL(fileURLWithPath: path), configuration: NSWorkspace.OpenConfiguration())
        }
        message = running.isEmpty ? "Abrindo o Claude Desktop…" : "Reabrindo o Claude Desktop para carregar as ferramentas…"
    }
    func chooseSamples() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = true
        panel.prompt = "Indexar samples"
        panel.message = "Escolha as pastas com seus samples e loops. O Claude passa a encontrá-los por papel, tom e BPM."
        if panel.runModal() == .OK, !panel.urls.isEmpty {
            perform("index_samples", params: ["folders": panel.urls.map(\.path)], timeout: 600) { _ in self.refresh() }
        }
    }
    func openLive() {
        let apps = (try? FileManager.default.contentsOfDirectory(atPath: "/Applications")) ?? []
        if let name = apps.sorted().last(where: { $0.hasPrefix("Ableton Live") && $0.hasSuffix(".app") }) {
            NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/" + name))
        } else { error = "Abra sua instalação do Ableton Live para continuar." }
    }
    func connectAccount(newAccount: Bool = false) {
        perform("auth_begin", params: ["new_account": newAccount]) { result in
            guard let raw = result["auth_url"] as? String, let url = URL(string: raw), url.host == "auth.openai.com", url.scheme == "https" else {
                self.error = "O endereço de login não foi confirmado."; return
            }
            NSWorkspace.shared.open(url)
            self.message = "Conclua o login e autorize o uso do seu plano no navegador. Depois, volte a este app."
        }
    }
    func cancelLogin() { perform("auth_cancel") }
    func refreshModels() { perform("auth_models", timeout: 60) }
    func selectAccount(_ id: String) { modelID = ""; perform("auth_select", params: ["account_id": id]) }
    func disconnectAccount() { modelID = ""; perform("auth_logout", timeout: 60) }
    func acknowledgePlan() {
        perform("auth_acknowledge") { _ in self.showPlanWelcome = false }
    }
    func send(_ text: String? = nil, approve: Bool? = nil) {
        guard !awaitingLogin else { error = "Conclua ou cancele o login antes de continuar a conversa."; return }
        let prompt = text ?? draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !prompt.isEmpty || approve != nil else { return }
        guard accountConnected && !modelID.isEmpty else { route = "settings"; error = "Continue com ChatGPT para conectar sua conta."; return }
        var params: [String: Any] = ["text": approve == nil ? prompt : "", "provider": provider,
                                    "model": modelID,
                                    "genre": activeGenre]
        if let approve { params["approve"] = approve }
        perform("chat", params: params) { result in
            self.snapshot["chat"] = result
            self.draft = ""
        }
    }
    func resetChat() { perform("reset_chat") { self.snapshot["chat"] = $0 } }
    func beginIdea(bars: Int, confirmed: Bool, label: String = "") {
        perform("production_begin", params: ["bars": bars, "copy_confirmed": confirmed, "label": label]) { self.snapshot["production"] = $0 }
    }
    func continueProject(label: String, goal: String, confirmed: Bool) {
        perform("production_existing", params: ["label": label, "goal": goal, "copy_confirmed": confirmed]) { self.snapshot["production"] = $0 }
    }
    func restoreProject(_ id: String) {
        perform("production_restore", params: ["project_id": id, "project_confirmed": true], timeout: 190) { self.snapshot["production"] = $0 }
    }
    func improveProject() {
        let goal = production["goal"] as? String ?? "diagnosis"
        let prompt = goal == "groove" ? "Analise o groove da track existente e proponha uma melhoria focada no encaixe entre bateria e baixo, preservando o motivo e a identidade." :
            goal == "arrangement" ? "Analise o arranjo existente e proponha uma melhoria de contraste, entradas e saídas, reutilizando o material que já existe." :
            goal == "mix" ? "Diagnostique a mix deste projeto em relação ao meu gênero aprendido. Proponha a melhoria de maior impacto, sem recriar a música." :
            "Faça um diagnóstico deste projeto existente: o que já funciona e qual é a próxima melhoria de maior impacto? Comece apenas pela leitura, sem aplicar mudanças."
        send(prompt)
    }
    func productionAction(_ action: String) {
        perform("production_" + action, params: ["project_confirmed": true], timeout: 190) { self.snapshot["production"] = $0 }
    }
    func developStage() {
        let prompt = productionStage == "loop" ? "Construa uma primeira ideia curta no intervalo desta sessão. Comece por um motivo marcante e uma base simples, usando meu gênero. Proponha ações executáveis para eu aplicar e ouvir, sem abrir o arranjo ainda." :
            productionStage == "groove" ? "Desenvolva o groove do loop que aprovei: encaixe kick e baixo, hats e percussão, com espaço e variações sutis. Preserve o motivo e trabalhe apenas no trecho curto desta sessão." :
            "Abra o arranjo a partir do groove aprovado. Reutilize o material em seções com entradas, saídas, transições e contraste de energia. Guarde o loop original como arquivo mutado depois de copiá-lo para as seções. Proponha a primeira etapa executável do arranjo."
        send(prompt)
    }
    func tool(_ name: String, args: [String: Any] = [:], completion: ((Any) -> Void)? = nil) {
        perform("mcp_call", params: ["tool": name, "args": args], timeout: 190) { result in
            if let data = result["data"] { completion?(data) }
        }
    }
    func transport(_ action: String) { tool("ableton_command", args: ["cmd": "transport", "args": ["action": action]]) }
    func inspect(_ track: [String: Any]) {
        tool("ableton_command", args: ["cmd": "get_track", "args": ["track": track["i"] ?? 0]]) {
            self.selectedTrack = $0 as? [String: Any] ?? [:]
        }
    }
    func startRender() {
        guard let start = Double(renderStart), let end = Double(renderEnd), start >= 1, end > start else {
            error = "Escolha um intervalo válido: o fim deve vir depois do início."; return
        }
        tool("render_start", args: ["start_bar": start, "end_bar": end, "name": "Studio preview"])
    }
    func chooseAnalysis() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.audio]; panel.canChooseDirectories = false
        panel.prompt = "Analisar áudio"
        if panel.runModal() == .OK, let url = panel.url { analyze(url.path) }
    }
    func analyze(_ path: String) {
        guard !activeGenre.isEmpty else { error = "Selecione um gênero aprendido para comparar."; return }
        reportFile = path
        tool("compare_to_genre", args: ["path": path, "genre": activeGenre]) { self.report = $0 as? [String: Any] ?? [:] }
    }
    func revealData() {
        try? FileManager.default.createDirectory(atPath: dataDirectory, withIntermediateDirectories: true)
        NSWorkspace.shared.open(URL(fileURLWithPath: dataDirectory))
    }
    func stop() {
        timer?.invalidate(); timeouts.values.forEach { $0.cancel() }
        output.fileHandleForReading.readabilityHandler = nil
        process?.terminationHandler = nil
        try? input.fileHandleForWriting.close()
        if process?.isRunning == true { process?.terminate() }
    }
}
