<?xml version="1.0" encoding="utf-8"?>
<!--
  Zitierstil „SZI DHBW Lörrach“ für die Quellenverwaltung von Word.
  Er folgt der Richtlinie für wissenschaftliche Arbeiten des SZI der DHBW Lörrach, Belege in der Fußnote.
  Autor: Finn Dallügge. Lizenz: The Unlicense.
-->
<xsl:stylesheet version="1.0" xmlns="http://www.w3.org/TR/REC-html40"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:b="http://schemas.openxmlformats.org/officeDocument/2006/bibliography"
    xmlns:msxsl="urn:schemas-microsoft-com:xslt" exclude-result-prefixes="#default b msxsl">
  <xsl:output method="html" encoding="us-ascii" indent="no"/>
  <xsl:strip-space elements="*"/>

  <!-- Gesetz: Misc ohne Autor und Herausgeber, mit Kurztitel -->
  <xsl:key name="gesetz"
      match="b:Source[b:SourceType = 'Misc' and b:ShortTitle and not(b:Author/b:Author | b:Author/b:Editor)]"
      use="generate-id()"/>

  <xsl:variable name="monate">
    <monat en="January">Januar</monat>
    <monat en="February">Februar</monat>
    <monat en="March">März</monat>
    <monat en="April">April</monat>
    <monat en="May">Mai</monat>
    <monat en="June">Juni</monat>
    <monat en="July">Juli</monat>
    <monat en="August">August</monat>
    <monat en="September">September</monat>
    <monat en="October">Oktober</monat>
    <monat en="November">November</monat>
    <monat en="December">Dezember</monat>
  </xsl:variable>

  <!-- Je Quellentyp die Rollen des Kopfs in ihrer Folge, für GetImportantFields weitere Personen und Felder -->
  <xsl:variable name="typen">
    <typ name="Book" kopf="Author Editor" felder="Edition City Publisher"/>
    <typ name="BookSection" kopf="Author" personen="Editor BookAuthor" felder="BookTitle Edition City Publisher Pages"/>
    <typ name="JournalArticle" kopf="Author" felder="JournalName Volume Issue Pages"/>
    <typ name="ArticleInAPeriodical" kopf="Author" felder="PeriodicalTitle Volume Issue City Edition Month Day Pages"/>
    <typ name="ConferenceProceedings" kopf="Author" personen="Editor" felder="ConferenceName City Publisher Pages"/>
    <typ name="Report" kopf="Author" felder="ThesisType Institution Publisher City"/>
    <typ name="InternetSite" kopf="Author Editor" felder="InternetSiteTitle ProductionCompany Version Month Day"/>
    <typ name="DocumentFromInternetSite" kopf="Author Editor"
        felder="InternetSiteTitle ProductionCompany Version Month Day"/>
    <typ name="ElectronicSource" kopf="Author Editor"
        felder="PublicationTitle Edition City Publisher ProductionCompany Month Day"/>
    <typ name="Art" kopf="Artist" felder="PublicationTitle Institution City Publisher Pages"/>
    <typ name="SoundRecording" kopf="Performer Artist Composer"
        felder="AlbumTitle ProductionCompany City RecordingNumber"/>
    <typ name="Performance" kopf="Performer Writer Director" felder="Theater City Month Day"/>
    <typ name="Film" kopf="Director Performer" felder="ProductionCompany Distributor"/>
    <typ name="Interview" kopf="Interviewee" personen="Interviewer"
        felder="BroadcastTitle Station Broadcaster Publisher City Month Day"/>
    <typ name="Patent" kopf="Inventor" felder="Type PatentNumber Month Day"/>
    <typ name="Case" kopf="Author" felder="Court CaseNumber Reporter City Month Day"/>
    <typ name="Misc" kopf="Author Editor"
        felder="ShortTitle PublicationTitle Edition Issue City Publisher Month Day Pages"/>
  </xsl:variable>

  <xsl:template match="/">
    <xsl:choose>
      <xsl:when test="b:XslVersion">2026</xsl:when>
      <xsl:when test="b:StyleNameLocalized">SZI DHBW Lörrach</xsl:when>
      <xsl:when test="b:GetImportantFields"><xsl:apply-templates/></xsl:when>
      <xsl:when test="b:Citation | b:Bibliography">
        <xsl:variable name="eingabe"><xsl:apply-templates mode="bereinigt"/></xsl:variable>
        <html><body><xsl:apply-templates select="msxsl:node-set($eingabe)/*"/></body></html>
      </xsl:when>
    </xsl:choose>
  </xsl:template>

  <!-- Quelle, Präfix und Stelle ohne Leerraum am Rand und doppelten Leerraum aus eingefügtem Text, ein leeres Feld
       der Quelle gilt als nicht eingetragen; das Suffix bleibt -->
  <xsl:template match="*" mode="bereinigt">
    <xsl:copy><xsl:apply-templates mode="bereinigt"/></xsl:copy>
  </xsl:template>

  <xsl:template match="b:Source//*[not(normalize-space())]" mode="bereinigt"/>

  <xsl:template match="b:Source//text() | b:Pages/text() | b:PagePrefix/text()" mode="bereinigt">
    <xsl:value-of select="normalize-space()"/>
  </xsl:template>

  <!-- Seiten mit Bindestrich wie „30-50“ der Richtlinie -->
  <xsl:template match="b:Source/b:Pages/text()" mode="bereinigt" priority="1">
    <xsl:value-of select="translate(normalize-space(), '&#8211;', '-')"/>
  </xsl:template>

  <!-- Grundansicht von Create Source: was der Stil ausgibt, ohne die seltenen Felder -->
  <xsl:template match="b:GetImportantFields">
    <xsl:variable name="typ" select="msxsl:node-set($typen)/*[@name = current()/b:SourceType]"/>
    <b:ImportantFields>
      <xsl:call-template name="felder">
        <xsl:with-param name="namen" select="concat($typ/@kopf, ' ', $typ/@personen)"/>
        <xsl:with-param name="pfad" select="'b:Author/b:*/b:NameList'"/>
      </xsl:call-template>
      <xsl:call-template name="felder">
        <xsl:with-param name="namen"
            select="concat('Title Year ', $typ/@felder, ' Comments URL YearAccessed MonthAccessed DayAccessed DOI')"/>
      </xsl:call-template>
    </b:ImportantFields>
  </xsl:template>

  <!-- Ein ImportantField je Name der Liste, * im Pfad steht für den Namen -->
  <xsl:template name="felder">
    <xsl:param name="namen"/>
    <xsl:param name="pfad" select="'b:*'"/>
    <xsl:if test="$namen">
      <xsl:variable name="name" select="substring-before(concat($namen, ' '), ' ')"/>
      <b:ImportantField>
        <xsl:value-of select="concat(substring-before($pfad, '*'), $name, substring-after($pfad, '*'))"/>
      </b:ImportantField>
      <xsl:call-template name="felder">
        <xsl:with-param name="namen" select="substring-after($namen, ' ')"/>
        <xsl:with-param name="pfad" select="$pfad"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <!-- Kurzbeleg einer Quelle; Word hängt die Aufrufe eines Felds aneinander, „; “ trennt sie -->
  <xsl:template match="b:Citation">
    <xsl:variable name="gesetz" select="key('gesetz', generate-id(b:Source))"/>
    <xsl:variable name="beleg">
      <teil><xsl:value-of select="b:PagePrefix"/></teil>
      <teil trenner=" "><xsl:value-of select="b:Pages[$gesetz]"/></teil>
      <teil trenner=" ">
        <xsl:apply-templates select="b:Source[not(../b:NoAuthor)]" mode="kopf">
          <xsl:with-param name="form" select="'kurz'"/>
        </xsl:apply-templates>
      </teil>
      <teil trenner=" "><xsl:apply-templates select="b:Source[not(../b:NoYear)]" mode="jahr"/></teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <teil><xsl:apply-templates select="b:Pages[not($gesetz)]" mode="stelle"/></teil>
      <teil trenner=""><xsl:value-of select="b:PageSuffix"/></teil>
    </xsl:variable>
    <xsl:choose>
      <!-- Platzhalter von Word: nur das Tag -->
      <xsl:when test="b:Source[not(b:SourceType)]"><xsl:value-of select="b:Source/b:Tag"/></xsl:when>
      <xsl:otherwise>
        <xsl:for-each select="msxsl:node-set($beleg)"><xsl:call-template name="verbinden"/></xsl:for-each>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:if test="not(b:LastAuthor)">; </xsl:if>
  </xsl:template>

  <!-- Ohne Platzhalter -->
  <xsl:template match="b:Bibliography">
    <xsl:variable name="eintraege"><xsl:apply-templates select="b:Source[b:SourceType]" mode="eintrag"/></xsl:variable>
    <xsl:for-each select="msxsl:node-set($eintraege)/*">
      <xsl:sort select="@kopf" lang="de" case-order="upper-first"/>
      <xsl:sort select="@jahr" lang="de" case-order="upper-first"/>
      <xsl:sort select="@titel" lang="de" case-order="upper-first"/>
      <xsl:copy-of select="*"/>
    </xsl:for-each>
  </xsl:template>

  <!-- Kopf. Rumpf. Netz. (Kommentar) -->
  <xsl:template match="b:Source" mode="eintrag">
    <xsl:variable name="kopf"><xsl:apply-templates select="." mode="kopf"/></xsl:variable>
    <xsl:variable name="jahr"><xsl:apply-templates select="." mode="jahr"/></xsl:variable>
    <xsl:variable name="saetze">
      <satz>
        <!-- ohne Name und Jahr „o.V., o.J.“ wie in der Richtlinie, auch mit Buchstaben „o.V., o.J.a“ -->
        <teil><xsl:value-of select="$kopf"/><xsl:if test="$kopf = 'o.V.' and starts-with($jahr, 'o.J.')">,</xsl:if></teil>
        <teil trenner=" "><xsl:value-of select="$jahr"/></teil>
      </satz>
      <xsl:apply-templates select="." mode="rumpf"/>
      <satz>
        <teil vor="[" nach="]"><xsl:value-of select="b:Medium"/></teil>
        <!-- jeder DOI beginnt mit „10.“, ein Vorsatz davor entfällt -->
        <teil trenner=" " vor="DOI: 10."><xsl:value-of select="substring-after(b:DOI, '10.')"/></teil>
        <teil trenner=" " vor="URL: "><xsl:value-of select="b:URL[not(../b:DOI)]"/></teil>
        <xsl:if test="b:URL | b:DOI">
          <teil trenner=" " vor="[Stand: " nach="]">
            <xsl:call-template name="datum">
              <xsl:with-param name="tag" select="b:DayAccessed"/>
              <xsl:with-param name="monat" select="b:MonthAccessed"/>
              <xsl:with-param name="jahr" select="b:YearAccessed"/>
            </xsl:call-template>
          </teil>
        </xsl:if>
      </satz>
    </xsl:variable>
    <eintrag kopf="{$kopf}" jahr="{$jahr}" titel="{b:Title}">
      <p class="MsoBibliography">
        <xsl:for-each select="msxsl:node-set($saetze)/*[string()]">
          <xsl:variable name="satz"><xsl:call-template name="verbinden"/></xsl:variable>
          <xsl:if test="position() &gt; 1"><xsl:text> </xsl:text></xsl:if>
          <xsl:copy-of select="$satz"/>
          <xsl:if test="not(contains('.?!', substring($satz, string-length($satz))))">.</xsl:if>
        </xsl:for-each>
        <xsl:if test="b:Comments and not(key('gesetz', generate-id()))">
          <xsl:value-of select="concat(' (', b:Comments, ')')"/>
        </xsl:if>
      </p>
    </eintrag>
  </xsl:template>

  <!-- Ein Teil ohne Inhalt entfällt samt Trenner, ohne eigenen Trenner gilt „, “ -->
  <xsl:template name="verbinden">
    <xsl:for-each select="*[string()]">
      <xsl:if test="position() &gt; 1">
        <xsl:value-of select="@trenner"/>
        <xsl:if test="not(@trenner)">, </xsl:if>
      </xsl:if>
      <xsl:value-of select="@vor"/>
      <xsl:copy-of select="node()"/>
      <xsl:value-of select="@nach"/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Book']" mode="rumpf">
    <satz>
      <teil><xsl:value-of select="b:Title"/></teil>
      <teil vor="übersetzt von "><xsl:apply-templates select="b:Author/b:Translator" mode="personen"/></teil>
      <!-- ohne Autor steht der Herausgeber im Kopf -->
      <teil vor="hg. von "><xsl:apply-templates select="b:Author/b:Editor[../b:Author]" mode="personen"/></teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <teil nach=" Bände"><xsl:value-of select="b:NumberVolumes[not(../b:Volume)]"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="auflage"/></teil>
      <xsl:call-template name="ort"/>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'BookSection']" mode="rumpf">
    <satz>
      <teil><xsl:value-of select="b:Title"/></teil>
      <teil vor="in ">
        <xsl:call-template name="urheber">
          <xsl:with-param name="rollen" select="'Editor BookAuthor'"/>
          <xsl:with-param name="nach"><xsl:if test="b:BookTitle">: </xsl:if></xsl:with-param>
        </xsl:call-template>
        <xsl:for-each select="b:BookTitle"><i><xsl:value-of select="."/></i></xsl:for-each>
      </teil>
      <teil vor="übersetzt von "><xsl:apply-templates select="b:Author/b:Translator" mode="personen"/></teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="auflage"/></teil>
      <xsl:call-template name="ort"/>
      <teil vor="Kapitel "><xsl:value-of select="b:ChapterNumber"/></teil>
      <teil><xsl:value-of select="b:Pages"/></teil>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <!-- Ohne Zeitschrift, Band und Heft folgen die Seiten dem Titel wie in Zotero -->
  <xsl:template match="b:Source[b:SourceType = 'JournalArticle']" mode="rumpf">
    <xsl:variable name="heft" select="b:JournalName | b:Volume | b:Issue"/>
    <satz>
      <teil><xsl:value-of select="b:Title"/></teil>
      <teil><xsl:value-of select="b:Pages[not($heft)]"/></teil>
    </satz>
    <satz>
      <xsl:call-template name="heft"><xsl:with-param name="zeitschrift" select="b:JournalName"/></xsl:call-template>
      <teil><xsl:value-of select="b:Pages[$heft]"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'ArticleInAPeriodical']" mode="rumpf">
    <satz>
      <teil><xsl:value-of select="b:Title"/></teil>
      <xsl:call-template name="heft"><xsl:with-param name="zeitschrift" select="b:PeriodicalTitle"/></xsl:call-template>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="auflage"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
      <teil><xsl:value-of select="b:Pages"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'ConferenceProceedings']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil vor="in ">
        <xsl:call-template name="urheber">
          <xsl:with-param name="rollen" select="'Editor'"/>
          <xsl:with-param name="nach"><xsl:if test="b:ConferenceName">: </xsl:if></xsl:with-param>
        </xsl:call-template>
        <xsl:value-of select="b:ConferenceName"/>
      </teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <xsl:call-template name="ort"/>
      <teil><xsl:value-of select="b:Pages"/></teil>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Report']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:ThesisType"/></teil>
      <teil><xsl:value-of select="b:Institution"/></teil>
      <teil><xsl:value-of select="b:Department"/></teil>
      <teil><xsl:value-of select="b:Publisher[not(. = ../b:Institution)]"/></teil>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'InternetSite' or b:SourceType = 'DocumentFromInternetSite']"
      mode="rumpf">
    <satz><teil><i><xsl:value-of select="b:Title"/></i></teil></satz>
    <satz>
      <teil><xsl:value-of select="b:InternetSiteTitle"/></teil>
      <teil><xsl:value-of select="b:ProductionCompany"/></teil>
      <teil><xsl:apply-templates select="b:Version" mode="version"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'ElectronicSource']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:PublicationTitle"/></teil>
      <teil vor="übersetzt von "><xsl:apply-templates select="b:Author/b:Translator" mode="personen"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="version"/></teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <xsl:call-template name="ort">
        <xsl:with-param name="verlag" select="b:Publisher | b:ProductionCompany[not(../b:Publisher)]"/>
      </xsl:call-template>
      <teil><xsl:call-template name="datum"/></teil>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Art']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:PublicationTitle"/></teil>
      <teil><xsl:value-of select="b:Institution"/></teil>
      <xsl:call-template name="ort"/>
      <teil><xsl:value-of select="b:Pages"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'SoundRecording']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:AlbumTitle"/></teil>
      <teil><xsl:value-of select="b:ProductionCompany"/></teil>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:value-of select="b:RecordingNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Performance']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:Theater"/></teil>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Film']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:ProductionCompany"/></teil>
      <teil><xsl:value-of select="b:Distributor"/></teil>
      <teil><xsl:value-of select="b:CountryRegion"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Interview']" mode="rumpf">
    <satz><teil><i><xsl:value-of select="b:Title"/></i></teil></satz>
    <satz>
      <teil>Interview</teil>
      <teil trenner=" " vor="mit "><xsl:apply-templates select="b:Author/b:Interviewer" mode="personen"/></teil>
      <teil><xsl:value-of select="b:BroadcastTitle"/></teil>
      <teil><xsl:value-of select="b:Station"/></teil>
      <teil><xsl:value-of select="b:Broadcaster"/></teil>
      <teil><xsl:value-of select="b:Publisher"/></teil>
    </satz>
    <satz>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Patent']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="normalize-space(concat(b:Type, ' ', b:PatentNumber))"/></teil>
      <teil><xsl:value-of select="b:CountryRegion"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[b:SourceType = 'Case']" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <!-- ohne Autor steht das Gericht im Kopf -->
      <teil><xsl:value-of select="b:Court[../b:Author/b:Author]"/></teil>
      <teil><xsl:value-of select="b:CaseNumber"/></teil>
      <teil><xsl:value-of select="b:Reporter"/></teil>
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:call-template name="datum"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source[key('gesetz', generate-id())]" mode="rumpf">
    <satz><teil vor="[" nach="]"><xsl:value-of select="b:Comments"/></teil></satz>
    <satz>
      <teil><xsl:value-of select="b:PublicationTitle"/></teil>
      <teil trenner=" "><xsl:value-of select="b:Volume"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="auflage"/></teil>
      <xsl:call-template name="ort"/>
      <teil><xsl:value-of select="b:Pages"/></teil>
    </satz>
  </xsl:template>

  <!-- Misc, auch E-Mail und Brief -->
  <xsl:template match="b:Source" mode="rumpf">
    <satz>
      <teil><i><xsl:value-of select="b:Title"/></i></teil>
      <teil><xsl:value-of select="b:PublicationTitle"/></teil>
      <teil vor="übersetzt von "><xsl:apply-templates select="b:Author/b:Translator" mode="personen"/></teil>
      <teil><xsl:apply-templates select="b:Edition" mode="auflage"/></teil>
      <teil vor="Band "><xsl:value-of select="b:Volume"/></teil>
      <teil trenner=" " vor="(" nach=")"><xsl:value-of select="b:Issue"/></teil>
      <xsl:call-template name="ort"/>
      <teil><xsl:call-template name="datum"/></teil>
      <teil><xsl:value-of select="b:Pages"/></teil>
      <teil><xsl:value-of select="b:StandardNumber"/></teil>
    </satz>
  </xsl:template>

  <xsl:template match="b:Source" mode="kopf">
    <xsl:param name="form" select="'lang'"/>
    <xsl:variable name="urheber">
      <xsl:call-template name="urheber">
        <xsl:with-param name="rollen" select="msxsl:node-set($typen)/*[@name = current()/b:SourceType]/@kopf"/>
        <xsl:with-param name="form" select="$form"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="gesetz" select="key('gesetz', generate-id())"/>
    <xsl:choose>
      <xsl:when test="string($urheber)"><xsl:value-of select="$urheber"/></xsl:when>
      <xsl:when test="b:Court"><xsl:value-of select="b:Court"/></xsl:when>
      <xsl:when test="$gesetz and b:Title and $form = 'lang'">
        <xsl:value-of select="concat(b:Title, ' (', b:ShortTitle, ')')"/>
      </xsl:when>
      <xsl:when test="$gesetz"><xsl:value-of select="b:ShortTitle"/></xsl:when>
      <xsl:otherwise>o.V.</xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="b:Source" mode="jahr">
    <xsl:value-of select="b:Year"/>
    <xsl:if test="not(b:Year)">o.J.</xsl:if>
  </xsl:template>

  <!-- Personen der ersten besetzten Rolle aus der Liste, der Herausgeber mit „(Hg.)“ -->
  <xsl:template name="urheber">
    <xsl:param name="rollen"/>
    <xsl:param name="form" select="'lang'"/>
    <xsl:param name="nach"/>
    <xsl:variable name="liste" select="concat(' ', $rollen, ' ')"/>
    <xsl:for-each select="b:Author/*[contains($liste, concat(' ', local-name(), ' '))]">
      <xsl:sort select="string-length(substring-before($liste, concat(' ', local-name(), ' ')))" data-type="number"/>
      <xsl:if test="position() = 1">
        <xsl:apply-templates select="." mode="personen">
          <xsl:with-param name="form" select="$form"/>
        </xsl:apply-templates>
        <xsl:if test="self::b:Editor"> (Hg.)</xsl:if>
        <xsl:value-of select="$nach"/>
      </xsl:if>
    </xsl:for-each>
  </xsl:template>

  <!-- Form lang „Nachname, V.“, kurz „Nachname“, text „Vorname Nachname“; ab vier Personen „et al.“ -->
  <xsl:template match="*" mode="personen">
    <xsl:param name="form" select="'text'"/>
    <xsl:value-of select="b:Corporate"/>
    <xsl:for-each select="b:NameList/b:Person[position() = 1 or last() &lt; 4]">
      <xsl:choose>
        <xsl:when test="position() = 1"/>
        <xsl:when test="position() = last()"> und </xsl:when>
        <xsl:when test="$form = 'lang'">; </xsl:when>
        <xsl:otherwise>, </xsl:otherwise>
      </xsl:choose>
      <xsl:choose>
        <xsl:when test="$form = 'text'">
          <xsl:value-of select="normalize-space(concat(b:First, ' ', b:Middle, ' ', b:Last))"/>
        </xsl:when>
        <xsl:otherwise><xsl:value-of select="b:Last"/></xsl:otherwise>
      </xsl:choose>
      <xsl:if test="$form = 'lang' and (b:First or b:Middle)">
        <xsl:text>, </xsl:text>
        <xsl:call-template name="initialen">
          <xsl:with-param name="namen" select="normalize-space(concat(b:First, ' ', b:Middle))"/>
        </xsl:call-template>
      </xsl:if>
    </xsl:for-each>
    <xsl:if test="b:NameList/b:Person[4]"> et al.</xsl:if>
  </xsl:template>

  <!-- „Hans-Dieter K.“ wird „H.-D. K.“: je Wort der erste Buchstabe, Gekürztes bleibt -->
  <xsl:template name="initialen">
    <xsl:param name="namen"/>
    <xsl:variable name="wort" select="substring-before(concat(translate($namen, '-', ' '), ' '), ' ')"/>
    <xsl:choose>
      <xsl:when test="contains($wort, '.')"><xsl:value-of select="$wort"/></xsl:when>
      <xsl:otherwise><xsl:value-of select="concat(substring($wort, 1, 1), '.')"/></xsl:otherwise>
    </xsl:choose>
    <xsl:if test="string-length($namen) &gt; string-length($wort)">
      <xsl:value-of select="substring($namen, string-length($wort) + 1, 1)"/>
      <xsl:call-template name="initialen">
        <xsl:with-param name="namen" select="substring($namen, string-length($wort) + 2)"/>
      </xsl:call-template>
    </xsl:if>
  </xsl:template>

  <!-- „3. Januar 2011“, ohne Monat kein Tag; ein Monat als Zahl oder englischer Name wird deutsch, sonst bleibt er -->
  <xsl:template name="datum">
    <xsl:param name="tag" select="b:Day"/>
    <xsl:param name="monat" select="b:Month"/>
    <xsl:param name="jahr"/>
    <xsl:variable name="deutsch" select="msxsl:node-set($monate)/*[position() = $monat or @en = $monat]"/>
    <xsl:variable name="datum">
      <xsl:choose>
        <xsl:when test="not($monat)"/>
        <xsl:when test="floor($tag) = $tag"><xsl:value-of select="number($tag)"/>.</xsl:when>
        <xsl:otherwise><xsl:value-of select="$tag"/></xsl:otherwise>
      </xsl:choose>
      <xsl:value-of select="concat(' ', $deutsch, $monat[not($deutsch)], ' ', $jahr)"/>
    </xsl:variable>
    <xsl:value-of select="normalize-space($datum)"/>
  </xsl:template>

  <!-- „*Zeitschrift* 52 (2)“ als ein Teil: Ohne Zeitschrift schließen Band und Heft mit Komma an wie in Zotero -->
  <xsl:template name="heft">
    <xsl:param name="zeitschrift"/>
    <xsl:variable name="heft">
      <teil><i><xsl:value-of select="$zeitschrift"/></i></teil>
      <teil trenner=" "><xsl:value-of select="b:Volume"/></teil>
      <teil trenner=" " vor="(" nach=")"><xsl:value-of select="b:Issue"/></teil>
    </xsl:variable>
    <teil><xsl:for-each select="msxsl:node-set($heft)"><xsl:call-template name="verbinden"/></xsl:for-each></teil>
  </xsl:template>

  <!-- „Stadt, Land: Verlag“, ohne Ort nur der Verlag -->
  <xsl:template name="ort">
    <xsl:param name="verlag" select="b:Publisher"/>
    <xsl:variable name="ort">
      <teil><xsl:value-of select="b:City"/></teil>
      <teil><xsl:value-of select="b:StateProvince"/></teil>
      <teil><xsl:value-of select="b:CountryRegion"/></teil>
      <teil trenner=": "><xsl:value-of select="$verlag"/></teil>
    </xsl:variable>
    <teil><xsl:for-each select="msxsl:node-set($ort)"><xsl:call-template name="verbinden"/></xsl:for-each></teil>
  </xsl:template>

  <!-- Eine ganze Zahl, auch „2.“, wird „2. Auflage“, sonst gibt die eingebaute Regel den Text aus -->
  <xsl:template match="b:Edition[floor(.) = .]" mode="auflage">
    <xsl:value-of select="concat(number(.), '. Auflage')"/>
  </xsl:template>

  <xsl:template match="b:Version | b:Edition" mode="version">
    <xsl:if test="contains('0123456789', substring(., 1, 1))">Version </xsl:if>
    <xsl:value-of select="."/>
  </xsl:template>

  <!-- Stelle nur aus Ziffern, Strichen, Kommas und Leerzeichen: „S. 33-35“ mit Bindestrich, sonst wie eingetragen -->
  <xsl:template match="b:Pages[translate(., '0123456789-&#8211;, ', '') = '']" mode="stelle">
    <xsl:value-of select="concat('S.&#160;', translate(., '&#8211;', '-'))"/>
  </xsl:template>
</xsl:stylesheet>
