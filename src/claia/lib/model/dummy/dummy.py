"""
A dummy model that returns a predefined story.
Used for testing streaming capabilities.
"""

# External dependencies
import time
import logging
import random
from typing import Dict, Any

# Internal dependencies
from ..base import BaseModel
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                             CONSTANTS                                #
########################################################################
STORY = """
In the ancient forests of Kyoto, where the mist clung to the towering cedar trees and whispers of old magic stirred in the undergrowth, lived a young kitsune named Akira. With fur as white as fresh snow and eyes gleaming like amber jewels, Akira was no ordinary fox. Born with eight tails—a sign of great power among her kind—she was destined for remarkable things. Yet despite her natural talents, Akira remained restless, yearning for adventure beyond the boundaries of the sacred woods that had been her home for nearly three hundred years.

The kitsune elders warned against venturing into the human world. "Humans have forgotten the old ways," they cautioned. "They no longer honor the spirits or respect the balance. They would trap you, study you, or worse." But Akira could not quiet her curious heart. She had mastered transformation long ago, able to shift between her fox form and that of a beautiful young woman with flowing black hair and ivory skin, her fox ears and tails hidden from mortal eyes through careful illusion.

On the night of the autumn equinox, when the veil between worlds thinned, Akira made her decision. Slipping away from the festival where her kin danced beneath the moonlight, she followed an ancient path that led out of the enchanted forest. The boundary between her realm and the human world was marked by a torii gate, vermilion pillars standing proud against the night sky. Akira hesitated for just a moment before passing through, feeling the tingle of magic as she crossed the threshold.

The modern world that greeted her was nothing like the Japan she remembered. Steel towers reached toward the heavens, strange metal contraptions roared along paved roads, and the air was thick with unfamiliar scents and sounds. Kyoto had transformed during her seclusion, modernized yet still retaining echoes of its traditional past. Shrines and temples stood defiantly among neon signs and crowded streets.

Adopting her human form, Akira wandered through the city, wide-eyed and enthralled. She wore a simple blue yukata she had conjured, her feet bare against the cool pavement. The humans paid her little mind, too absorbed in their own hurried lives to notice the supernatural being in their midst. Only a few—a child clutching his mother's hand, an elderly woman sweeping the steps of a shrine—gave her curious glances, as if sensing something unusual about the beautiful young woman with the too-bright eyes.

Drawn by the scent of fried food and sweet treats, Akira found herself at a bustling night market. Lanterns strung overhead cast a warm glow over stalls selling everything from traditional crafts to modern trinkets. Her stomach rumbled, reminding her that even magical beings required sustenance. With a flick of her wrist, she conjured a few coins—another kitsune trick—and approached a vendor selling taiyaki, fish-shaped cakes filled with sweet red bean paste.

"One, please," she said, her voice melodious but slightly accented with an old-fashioned dialect.

The vendor, a middle-aged man with laugh lines around his eyes, handed her the steaming treat. "You speak like my grandmother," he chuckled. "Not many young people use such formal Japanese anymore."

Akira merely smiled, accepting the taiyaki with a small bow. As she turned to leave, the vendor called after her, "Be careful tonight, miss. Strange things happen during the equinox."

If only he knew how strange things truly were, Akira thought with amusement, taking a bite of the warm cake. The sweetness exploded on her tongue, and she closed her eyes in delight. When she opened them again, she noticed a man watching her from across the market. Tall and lean, with sharp features and eyes that seemed to gleam in the lantern light, he stood perfectly still amid the moving crowd.

A shiver ran down Akira's spine. There was something familiar about him, something not entirely human. Their eyes met, and a knowing smile curved his lips. With a slight nod, he turned and disappeared into an alleyway.

Curious and perhaps a bit reckless, Akira followed. The alley was narrow and dark, leading away from the noise and light of the market. She should have been cautious—kitsune were not the only supernatural beings in Japan, and not all were friendly—but the thrill of potential discovery pulled her forward.

The alley opened into a small courtyard, where an ancient maple tree spread its branches over a tiny shrine, almost hidden between modern buildings. The man stood beneath the tree, his form shifting in the shadows.

"It's been a long time since a kitsune of your power ventured into the human realm," he said, his voice a low rumble. "What brings you here, eight-tails?"

Akira stiffened, instinctively drawing her power around her like a cloak. "How did you know what I am?"

The man laughed, and his form rippled, revealing midnight-black fur and four tails fanning behind him. Another kitsune, but one with darker power than her own.

"I am Kuro," he said, his human form returning. "These humans believe they have claimed this land for themselves, but some of us never left. We adapted, learned their ways, and found new methods to thrive."

"The elders said no kitsune remained in the human world," Akira said, taking a step back.

"The elders prefer their isolation," Kuro replied with a shrug. "But there is power to be found here, in the beliefs and fears of humans. They may have forgotten the old ways, but they still feel them in their souls." His eyes gleamed with ambition. "Join me, Akira. With your power and mine, we could awaken the old magic fully in this place."

Akira sensed the danger in his offer. Kuro was not speaking of harmony but of exploitation. "How do you know my name?"

"Word travels fast among our kind," he said, taking a step closer. "And a kitsune with eight tails is rare indeed. You're nearly a divine being. Think of what we could accomplish together."

Before Akira could respond, a soft meow interrupted them. A calico cat sat on the shrine steps, watching them with unblinking green eyes. There was intelligence in that gaze, too much for an ordinary cat.

Kuro hissed, his composure breaking. "Bakeneko, this doesn't concern you."

The cat's tail twitched, and it spoke in a woman's voice. "When dark kitsune plot in my territory, it becomes my concern." In a fluid motion, the cat transformed into a woman with calico-patterned kimono and ears that remained decidedly feline. "Especially when they threaten visitors."

"I made no threats," Kuro said coolly.

"Perhaps not with words," the cat woman replied. She turned to Akira. "I am Hana, guardian of this district. Kuro and his followers have been causing mischief, feeding on fear rather than respect. They've forgotten the true way of our kinds."

Akira looked between them, sensing an old conflict. "I didn't come seeking trouble. I only wanted to explore."

Hana's expression softened. "Exploration is well and good, but these are complicated times. Humans have forgotten much, but some remember or are beginning to remember. There is a balance to be maintained."

A distant bell tolled, and Kuro glanced up at the sky. "Dawn approaches. Consider my offer, Akira. Find me when you tire of playing by the old rules." With that, he shifted into his fox form—a black fox with gleaming red eyes—and darted away into the shadows.

Hana sighed. "He grows bolder. There are others like him, spirits who see humans only as a resource to be exploited." She fixed Akira with a penetrating gaze. "But there are also those of us who believe in coexistence, in guiding rather than controlling. We could use someone of your power."

Akira hesitated. She had come seeking adventure, not to be caught in a supernatural conflict. And yet, was this not exactly the kind of purpose she had been missing? "What exactly is happening here?"

"Walk with me," Hana said, already moving toward the alley. "Dawn is not kind to those with too much yokai blood, and we have much to discuss."

As they left the courtyard, Akira felt the first stirrings of true excitement. Her impulsive journey into the human world had led her to something far more significant than sightseeing. There was a battle for balance unfolding in modern Kyoto, hidden behind illusions and modern distractions.

For the first time in decades, Akira felt truly alive. This was the adventure she had been seeking—not just to observe the human world but to find her place within it. As she followed Hana through the awakening city, her eight tails invisible but full of power, she knew that her life was about to change forever.

The sun broke over the horizon, painting the city in gold. A new day, and for Akira, the beginning of an extraordinary journey that would test her powers, her courage, and her heart. The ancient magic of Japan was stirring, and she would be at the center of its awakening.
"""

CHARS_PER_SECOND = 2000
CHARS_PER_CHUNK = 20



########################################################################
#                               CLASSES                                #
########################################################################
class DummyModel(BaseModel):
  """
  A dummy model that returns a predefined story.
  This model simulates streaming by returning chunks of the story
  at a controlled rate.
  """
  def __init__(self, model_name: str = "dummy-model"):
    super().__init__(model_name)
    self.story = STORY.strip()
    self.characters = list(self.story)
    self.story_length = len(self.characters)
    logger.debug(f"Initialized DummyModel with {self.story_length} characters")

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """
    Generate a response by streaming a predefined story.

    Args:
        conversation: The conversation to add the response to
        **kwargs: Additional parameters, including:
            - chars_per_second: How many characters to return per second (default: 100)
            - chars_per_chunk: How many characters to send per chunk (default: 20)

    Returns:
        The complete story after streaming is finished
    """
    # Get the streaming rate
    chars_per_second = kwargs.get("chars_per_second", CHARS_PER_SECOND)
    chars_per_chunk = kwargs.get("chars_per_chunk", CHARS_PER_CHUNK)
    logger.debug(f"Generating response at {chars_per_second} characters per second in chunks of {chars_per_chunk}")

    # Add a blank assistant message to the conversation that we'll update
    message = conversation.add_message(MessageRole.ASSISTANT, "")

    # Simulate streaming by adding characters in chunks
    for i in range(0, self.story_length, chars_per_chunk):
        end_idx = min(i + chars_per_chunk, self.story_length)
        chunk = "".join(self.characters[i:end_idx])
        # Stream only the new chunk, appending to the message
        conversation.stream_message(message.message_id, chunk, append=True)
        delay = (chars_per_chunk / chars_per_second) * (0.9 + (random.random() * 0.2))
        time.sleep(delay)

    # Append a newline and mark the end of the stream
    conversation.stream_message(message.message_id, "\n", append=True, end=True)

    return message.content
