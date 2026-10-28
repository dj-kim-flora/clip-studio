// On-device transcription with word timings (macOS 26+ SpeechAnalyzer).
// Usage: transcribe <audio file> <out.json> [locale]
import AVFoundation
import Foundation
import Speech

struct Word: Codable { let t: String; let s: Double; let e: Double }
struct Segment: Codable { let s: Double; let e: Double; let text: String; let words: [Word] }

@main
struct Transcribe {
  static func main() async throws {
    let args = CommandLine.arguments
    guard args.count >= 3 else {
      FileHandle.standardError.write("usage: transcribe <audio> <out.json> [locale]\n".data(using: .utf8)!)
      exit(2)
    }
    let input = URL(fileURLWithPath: args[1])
    let output = URL(fileURLWithPath: args[2])
    let wanted = Locale(identifier: args.count > 3 ? args[3] : "en-US")
    guard let locale = await SpeechTranscriber.supportedLocale(equivalentTo: wanted) else {
      FileHandle.standardError.write("locale not supported\n".data(using: .utf8)!)
      exit(1)
    }
    let transcriber = SpeechTranscriber(
      locale: locale, transcriptionOptions: [], reportingOptions: [],
      attributeOptions: [.audioTimeRange])
    if let request = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
      FileHandle.standardError.write("installing speech assets…\n".data(using: .utf8)!)
      try await request.downloadAndInstall()
    }
    let analyzer = SpeechAnalyzer(modules: [transcriber])
    let file = try AVAudioFile(forReading: input)
    let total = Double(file.length) / file.processingFormat.sampleRate

    let collector = Task { () throws -> [Segment] in
      var segments: [Segment] = []
      for try await result in transcriber.results {
        var words: [Word] = []
        for run in result.text.runs {
          let piece = String(result.text[run.range].characters)
          if let range = run.audioTimeRange {
            words.append(Word(t: piece, s: range.start.seconds, e: range.end.seconds))
          } else if var last = words.popLast() {
            last = Word(t: last.t + piece, s: last.s, e: last.e)
            words.append(last)
          }
        }
        let text = String(result.text.characters)
        let s = result.range.start.seconds, e = result.range.end.seconds
        segments.append(Segment(s: s, e: e, text: text, words: words))
        let pct = Int(100 * e / max(total, 1))
        FileHandle.standardError.write("\r\(pct)%  ".data(using: .utf8)!)
      }
      return segments
    }
    if let last = try await analyzer.analyzeSequence(from: file) {
      try await analyzer.finalizeAndFinish(through: last)
    } else {
      await analyzer.cancelAndFinishNow()
    }
    let segments = try await collector.value
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted]
    try encoder.encode(segments).write(to: output)
    FileHandle.standardError.write("\nwrote \(segments.count) segments\n".data(using: .utf8)!)
  }
}
